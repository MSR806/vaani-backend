from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import (
    SceneCreate,
    SceneUpdate,
    SceneReorderRequest,
)
from ..services.scene_service import (
    create_scene,
    update_scene,
    get_scenes,
    delete_scene,
    reorder_scenes,
)
from ..auth import require_write_permission, require_delete_permission

router = APIRouter(tags=["scenes"])


@router.post("/scenes")
def create_scene_route(
    scene: SceneCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    return create_scene(db, scene, current_user["user_id"])

@router.put("/scenes/reorder")
def reorder_scenes_route(
    reorder_request: SceneReorderRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    scene_updates = [{"id": scene.id, "scene_number": scene.scene_number} for scene in reorder_request.scenes]
    
    updated_scenes = reorder_scenes(db, scene_updates)
    
    if updated_scenes is None:
        raise HTTPException(status_code=404, detail="One or more scenes not found or scenes from different chapters")
    
    return updated_scenes


@router.put("/scenes/{scene_id}")
def update_scene_route(
    scene_id: int, 
    scene_update: SceneUpdate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    scene = update_scene(db, scene_id, scene_update, current_user["user_id"])
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene

@router.get("/scenes")
def get_scenes_route(chapter_id: int = None, db: Session = Depends(get_db)):
    return get_scenes(db, chapter_id)

@router.delete("/scenes/{scene_id}")
def delete_scene_route(
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_delete_permission)
):
    success = delete_scene(db, scene_id, current_user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Scene not found")
    return {"message": "Scene deleted successfully"}
