from sqlalchemy.orm import Session
from fastapi import HTTPException
import requests
from ..models.models import Image
import io
import time
from app.utils.exceptions import rollback_on_exception


async def store_image_from_url(
    db: Session, url: str, name: str = "image", user_id: str = None
) -> Image:
    """
    Download an image from a URL and store it in the database.

    Args:
        db: Database session
        url: URL of the image to download
        name: Name to give the image
        user_id: ID of the user creating the image

    Returns:
        The created Image object
    """
    try:
        # Download the image
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Get the content type
        mime_type = response.headers.get("Content-Type", "image/jpeg")

        current_time = int(time.time())
        # Create a new image record
        db_image = Image(
            name=name,
            mime_type=mime_type,
            data=response.content,
            external_url=url,  # Store the original external URL
            created_at=current_time,
            updated_at=current_time,
            created_by=user_id,
            updated_by=user_id,
        )

        # Save to database
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        return db_image

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to download image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store image: {str(e)}")


def get_image(db: Session, image_id: int) -> Image:
    """
    Retrieve an image from the database by ID.

    Args:
        db: Database session
        image_id: ID of the image to retrieve

    Returns:
        The Image object if found, None otherwise
    """
    return db.query(Image).filter(Image.id == image_id).first()


@rollback_on_exception
def delete_image(db: Session, image_id: int, user_id: str = None) -> bool:
    """
    Delete an image from the database.

    Args:
        db: Database session
        image_id: ID of the image to delete
        user_id: ID of the user deleting the image

    Returns:
        True if the image was deleted, False otherwise
    """
    image = get_image(db, image_id)
    if not image:
        return False

    db.delete(image)
    db.commit()
    return True
