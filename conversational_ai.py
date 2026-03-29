"""
PolyHedge - Conversational RAG over local Polymarket data
Uses: LangChain + Ollama (local LLM) + FAISS vector store
Supports: JSON and CSV market data files
"""

import os
import json
import glob
import pandas as pd
from pathlib import Path
from langchain_ollama import OllamaLLM, OllamaEmbeddings
#from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.memory  import ConversationBufferMemory
from langchain_classic.schema import Document
from langchain_core.prompts import ChatPromptTemplate,PromptTemplate
import pandas as pd
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR = "data"          # folder containing your JSON/CSV files
OLLAMA_MODEL = "llama3.1:8b"      # change to any model you have pulled e.g. mistral, gemma
EMBED_MODEL = "nomic-embed-text"  # ollama pull nomic-embed-text
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

# ── 1. Load Data ──────────────────────────────────────────────────────────────

def load_json_file(path: str) -> list[Document]:
    """Load a JSON file — handles both list of records and single dict."""
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    docs = []
    for record in data:
        # Flatten the record into readable text so the LLM can reason over it
        text = "\n".join(f"{k}: {v}" for k, v in record.items())
        docs.append(Document(
            page_content=text,
            metadata={"source": path, "type": "json"}
        ))
    return docs


def load_csv_file(path: str) -> list[Document]:
    """Load a CSV file — each row becomes a Document."""
    df = pd.read_csv(path)
    docs = []
    for _, row in df.iterrows():
        text = "\n".join(f"{col}: {row[col]}" for col in df.columns)
        docs.append(Document(
            page_content=text,
            metadata={"source": path, "type": "csv"}
        ))
    return docs

def load_all_data(data_dir: str) -> list[Document]:
    """Recursively load all JSON and CSV files from the data directory."""
    all_docs = []
    path = Path(data_dir)

    json_files = list(path.glob("**/*.json"))
    csv_files = list(path.glob("**/*.csv"))

    print(f"📂 Found {len(json_files)} JSON file(s), {len(csv_files)} CSV file(s)")

    for f in json_files:
        try:
            docs = load_json_file(str(f))
            all_docs.extend(docs)
            print(f"  ✅ Loaded {str(f)} → {len(docs)} records")
        except Exception as e:
            print(f"  ❌ Failed to load {f}: {e}")

    for f in csv_files:
        try:
            docs = load_csv_file(str(f))
            all_docs.extend(docs)
            print(f"  ✅ Loaded {str(f)} → {len(docs)} rows")
        except Exception as e:
            print(f"  ❌ Failed to load {f}: {e}")

    return all_docs

# ── 2. Build Vector Store ─────────────────────────────────────────────────────

def build_vectorstore(docs: list[Document]) -> FAISS:
    """Chunk docs and embed them into a FAISS vector store."""
    print("\n🔨 Chunking and embedding documents...")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    print(f"  📄 {len(docs)} documents → {len(chunks)} chunks")

    model_name = "all-MiniLM-L6-v2"
    model_kwargs = {'device': 'cpu'} # Change to 'cuda' if you have an NVIDIA GPU
    encode_kwargs = {'normalize_embeddings': False}

    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

    print("loaded embeddings")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    print("  ✅ Vector store built")
    vectorstore.save_local("faiss store")
    return vectorstore

  
# ── 3. Build RAG Chain ────────────────────────────────────────────────────────

def build_chain(vectorstore: FAISS) :
    """Wire up the conversational RAG chain with memory."""
    from langchain_groq import ChatGroq

    llm = ChatGroq(
        model="openai/gpt-oss-120b",  # or any model below
        temperature=0,
        api_key=""    # or set GROQ_API_KEY in .env
    )
    prompt = ChatPromptTemplate.from_template("""
    You are an expert analyst for Polymarket prediction market data.
You have access to historical market data, trade records, and price movements.
Answer questions about what has happened in these markets — probabilities, volume, price changes, 
resolved outcomes, and trading patterns.

Be specific and reference actual data when answering.
If the answer isn't in the provided context, say so clearly — don't hallucinate.
Use TradFi language when relevant (e.g., "the market traded up to 0.74", "volume spiked", etc.)

Remember you are here to help the trader make better decisions !

Context from market data:
{context}

Question: {question} """)

    # 5. Helper to format retrieved docs
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    retriever = vectorstore.as_retriever(
    search_type="similarity",       # or "mmr" for diversity
    search_kwargs={"k": 8}
)

    # 6. LCEL RAG chain
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


# ── 4. Conversational Loop ────────────────────────────────────────────────────
def print_sources(source_docs: list[Document]):
    """Print the source chunks the answer was grounded in."""
    seen = set()
    for doc in source_docs:
        src = doc.metadata.get("source", "unknown")
        if src not in seen:
            print(f"    📎 {src}")
            seen.add(src)


def run_chat(chain):
    """Main conversational while loop."""
    print("\n" + "="*60)
    print("  PolyHedge AI — Ask anything about your market data")
    print("  Type 'exit' or 'quit' to stop | 'sources' to toggle source display")
    print("="*60 + "\n")

    show_sources = False

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        if user_input.lower() == "sources":
            show_sources = not show_sources
            print(f"  [Source display {'ON' if show_sources else 'OFF'}]\n")
            continue

        if user_input.lower() == "clear":
            chain.memory.clear()
            print("  [Conversation memory cleared]\n")
            continue

        try:
            result = chain.invoke(user_input)
            answer = str(result)
            print(f"\nPolyHedge: {answer}\n")

        except Exception as e:
            print(f"\n⚠️  Error: {e}\n")

def main():
    # Check data dir exists
    if not os.path.exists(DATA_DIR):
        print(f"❌ Data directory '{DATA_DIR}' not found.")
        print("   Create it and drop your JSON/CSV Polymarket data files in.")
        return

    # Load → Embed → Chat
    docs = load_all_data(DATA_DIR)
    if not docs:
        print("❌ No documents loaded. Check your data directory.")
        return

    vectorstore = build_vectorstore(docs)
    chain = build_chain(vectorstore)
    run_chat(chain)


if __name__ == "__main__":
    main()

