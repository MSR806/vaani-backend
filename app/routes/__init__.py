from fastapi import APIRouter
from .books import router as books_router
from .chapters import router as chapters_router
from .scenes import router as scenes_router
from .chat import router as chat_router
from .images import router as images_router
from .settings import router as settings_router
from .templates import router as templates_router
from .storyboard import router as storyboard_router
from .character_arcs import router as character_arcs_router
from .plot_beats import router as plot_beats_router
from .prompts import router as prompts_router


# Create a main router that includes all the individual routers
router = APIRouter()

# Include all routers
router.include_router(books_router)
router.include_router(chapters_router)
router.include_router(scenes_router)
router.include_router(chat_router)
router.include_router(images_router)
router.include_router(settings_router)
router.include_router(templates_router)
router.include_router(storyboard_router)
router.include_router(character_arcs_router)
router.include_router(plot_beats_router)
router.include_router(prompts_router)
