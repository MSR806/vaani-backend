from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.image_service import get_image

router = APIRouter(tags=["images"])


@router.get("/images/{image_id}")
async def get_image_route(image_id: int, db: Session = Depends(get_db)):
    """
    Retrieve an image from the database by ID and serve it with the appropriate content type.

    Args:
        image_id: ID of the image to retrieve
        db: Database session

    Returns:
        The image data with the appropriate content type
    """
    # Get the image from the database
    image = get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Return the image data with the appropriate content type
    return Response(content=image.data, media_type=image.mime_type)
