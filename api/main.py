from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import backtest, fusion, market, ml, polymarket, strategy, watchlist

app = FastAPI(title="Rentwise Quant Lab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/api")
app.include_router(strategy.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(ml.router, prefix="/api")
app.include_router(polymarket.router, prefix="/api")
app.include_router(fusion.router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
