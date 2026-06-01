"""FastAPI monitoring app.

Run with:
    uvicorn monitoring.api.main:app --reload --port 8000
"""

from fastapi import FastAPI

from monitoring.api.routes import health, metrics

app = FastAPI(
    title="Alt Cards Pipeline Monitor",
    description="Real-time pipeline health and metrics API",
    version="1.0.0",
)

app.include_router(health.router, prefix="/pipeline", tags=["health"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
