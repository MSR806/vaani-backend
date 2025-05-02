from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import (
    SceneCreate,
    SceneUpdate,
    SceneOutlineRequest,
    SceneCompletionRequest,
)
from ..services.scene_service import (
    create_scene,
    update_scene,
    get_scenes,
    generate_scene_outline,
    generate_scene_content,
)

router = APIRouter(tags=["scenes"])


@router.post("/scenes")
def create_scene_route(scene: SceneCreate, db: Session = Depends(get_db)):
    return create_scene(db, scene)


@router.put("/scenes/{scene_id}")
def update_scene_route(
    scene_id: int, scene_update: SceneUpdate, db: Session = Depends(get_db)
):
    scene = update_scene(db, scene_id, scene_update)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.get("/scenes")
def get_scenes_route(chapter_id: int = None, db: Session = Depends(get_db)):
    return get_scenes(db, chapter_id)


@router.post("/scenes/{scene_id}/generate-outline")
async def generate_scene_outline_route(
    scene_id: int, request: SceneOutlineRequest, db: Session = Depends(get_db)
):
    return await generate_scene_outline(db, scene_id, request)


@router.post("/scenes/{scene_id}/completion")
async def generate_scene_content_route(
    scene_id: int, request: SceneCompletionRequest, db: Session = Depends(get_db)
):
    return await generate_scene_content(db, scene_id, request)
