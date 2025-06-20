import logging

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_current_user
from app.database import Base, engine
from app.logging_config import configure_logging
from app.middleware.logger import RequestResponseLoggerMiddleware
from app.routes import router

Base.metadata.create_all(bind=engine)
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
logger = logging.getLogger(__name__)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestResponseLoggerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/vaani/api/v1", dependencies=[Depends(get_current_user)])


@app.get("/", tags=["public"])
async def root():
    return {
        "message": "Welcome to Vaani API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/vaani/health", tags=["public"])
async def health_check():
    logger.info("Health check")
    return {"status": "healthy", "api": "Vaani API", "version": "1.0.0"}
