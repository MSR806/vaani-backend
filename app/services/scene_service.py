from sqlalchemy.orm import Session, joinedload
from ..models.models import Scene, Chapter
from ..schemas.schemas import SceneCreate, SceneUpdate
import time
from app.utils.exceptions import rollback_on_exception


@rollback_on_exception
def create_scene(db: Session, scene: SceneCreate, user_id: str):
    # Check if chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None

    current_time = int(time.time())
    # Create the scene
    db_scene = Scene(
        scene_number=scene.scene_number,
        title=scene.title,
        chapter_id=scene.chapter_id,
        content=scene.content,
        created_at=current_time,
        updated_at=current_time,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene


@rollback_on_exception
def update_scene(db: Session, scene_id: int, scene_update: SceneUpdate, user_id: str):
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return None

    current_time = int(time.time())
    if scene_update.scene_number is not None:
        scene.scene_number = scene_update.scene_number
    if scene_update.title is not None:
        scene.title = scene_update.title
    if scene_update.content is not None:
        scene.content = scene_update.content

    scene.updated_at = current_time
    scene.updated_by = user_id

    db.commit()
    db.refresh(scene)
    return scene


def get_scene(db: Session, scene_id: int):
    return db.query(Scene).filter(Scene.id == scene_id).first()


def get_scenes(db: Session, chapter_id: int = None):
    query = db.query(Scene)
    if chapter_id is not None:
        query = query.filter(Scene.chapter_id == chapter_id)
    return query.all()


@rollback_on_exception
def delete_scene(db: Session, scene_id: int, user_id: str):
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return False

    # Get the scene's chapter_id and scene_number before deleting
    chapter_id = scene.chapter_id
    deleted_scene_number = scene.scene_number

    # Delete the scene
    db.delete(scene)

    # Update the scene numbers for all subsequent scenes in the same chapter
    scenes_to_update = (
        db.query(Scene)
        .filter(Scene.chapter_id == chapter_id, Scene.scene_number > deleted_scene_number)
        .order_by(Scene.scene_number)
        .all()
    )

    current_time = int(time.time())
    # Decrement scene_number for each subsequent scene and update audit fields
    for scene_to_update in scenes_to_update:
        scene_to_update.scene_number -= 1
        scene_to_update.updated_at = current_time
        scene_to_update.updated_by = user_id

    # Commit all changes
    db.commit()
    return True


@rollback_on_exception
def reorder_scenes(db: Session, scene_updates: list):
    """
    Reorder scenes based on the provided scene_id and new scene_number pairs.

    Args:
        db: Database session
        scene_updates: List of dictionaries with scene_id and new scene_number

    Returns:
        List of updated scenes or None if any scene is not found
    """
    # Collect all scenes to update - ensure scene IDs are integers
    scene_ids = [int(scene_update["id"]) for scene_update in scene_updates]
    scenes = db.query(Scene).filter(Scene.id.in_(scene_ids)).all()

    # Create a mapping of scene_id to scene object
    scene_map = {scene.id: scene for scene in scenes}

    # Check if all scenes exist
    if len(scenes) != len(scene_updates):
        return None

    # Get the chapter_id from the first scene (all scenes should be in the same chapter)
    if not scenes:
        return None

    chapter_id = scenes[0].chapter_id

    # Ensure all scenes belong to the same chapter
    if not all(scene.chapter_id == chapter_id for scene in scenes):
        return None

    # Apply the new scene numbers - ensure scene numbers are integers
    for scene_update in scene_updates:
        scene_id = int(scene_update["id"])
        new_scene_number = int(scene_update["scene_number"])

        if scene_id in scene_map:
            scene_map[scene_id].scene_number = new_scene_number

    # Commit the changes
    db.commit()

    # Refresh the scenes to get the updated values
    updated_scenes = []
    for scene_id in scene_ids:
        db.refresh(scene_map[scene_id])
        updated_scenes.append(scene_map[scene_id])

    return updated_scenes
