import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from db.client import get_bq_client
from cache import clear_cache
from routes import coverage, fighters, market, movers

app = FastAPI(
    title="Alt Cards Market Intelligence API",
    version="1.0.0",
)

_allowed_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/market", tags=["market"])
app.include_router(fighters.router, prefix="/fighters", tags=["fighters"])
app.include_router(movers.router, prefix="/movers", tags=["movers"])
app.include_router(coverage.router, prefix="/coverage", tags=["coverage"])


@app.on_event("startup")
async def verify_bq_connection() -> None:
    client = get_bq_client()
    client.query("SELECT 1").result()


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}


_CACHE_CLEAR_SECRET = os.getenv("CACHE_CLEAR_SECRET", "")


@app.get("/cache/clear", tags=["ops"])
def cache_clear(x_secret: str = Header("")):
    if _CACHE_CLEAR_SECRET and x_secret != _CACHE_CLEAR_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    count = clear_cache()
    return {"cleared": count}
