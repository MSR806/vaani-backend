import logging

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_current_user
from app.logging_config import configure_logging
from app.metrics.router import MetricsRouter
from app.routes import router as api_router

app = FastAPI(
    title="Vaani API",
    description="An API for managing books, chapters, scenes, and characters with AI assistance",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "auth",
            "description": "Authentication endpoints",
        },
    ],
    on_startup=[configure_logging],
)
utils_router = MetricsRouter()
logger = logging.getLogger(__name__)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Initializing metrics collection")


@app.get("/", tags=["public"])
async def root():
    return {
        "message": "Welcome to Vaani API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


@utils_router.get("/health/{health_id}/yo", tags=["public"])
async def health_check(health_id: int):
    return {"status": f"healthy {health_id}", "api": "Vaani API", "version": "1.0.0"}


app.include_router(api_router, prefix="/vaani/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(utils_router, prefix="/vaani/utils")
