from fastapi import APIRouter
from .books import router as books_router
from .chapters import router as chapters_router
from .characters import router as characters_router
from .scenes import router as scenes_router
from .chat import router as chat_router
from .images import router as images_router
from .settings import router as settings_router
from .templates import router as templates_router

# Create a main router that includes all the individual routers
router = APIRouter()

# Include all routers
router.include_router(books_router)
router.include_router(chapters_router)
router.include_router(characters_router)
router.include_router(scenes_router)
router.include_router(chat_router)
router.include_router(images_router)
router.include_router(settings_router)
router.include_router(templates_router)
