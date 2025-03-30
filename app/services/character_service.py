from sqlalchemy.orm import Session
from ..models.models import Character, Book, Chapter
from ..schemas.schemas import (
    CharacterCreate, CharacterUpdate, CharacterResponse,
    ChapterCharactersResponse, ExtractedCharacter
)
from ..services.ai_service import get_openai_client
from ..config import OPENAI_MODEL
import json

def create_character(db: Session, character: CharacterCreate):
    # Check if book exists
    book = db.query(Book).filter(Book.id == character.book_id).first()
    if not book:
        return None
    
    db_character = Character(
        name=character.name,
        description=character.description,
        book_id=character.book_id
    )
    db.add(db_character)
    db.commit()
    db.refresh(db_character)
    return db_character

def update_character(db: Session, character_id: int, character_update: CharacterUpdate):
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        return None
    
    if character_update.name is not None:
        character.name = character_update.name
    if character_update.description is not None:
        character.description = character_update.description
    
    db.commit()
    db.refresh(character)
    return character

def get_character(db: Session, character_id: int):
    return db.query(Character).filter(Character.id == character_id).first()

def get_characters(db: Session, book_id: int = None):
    query = db.query(Character)
    if book_id is not None:
        query = query.filter(Character.book_id == book_id)
    return query.all()

async def extract_chapter_characters(db: Session, chapter_id: int):
    # Get the chapter
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        return None
    
    # Prepare the messages for GPT
    messages = [
        {
            "role": "system",
            "content": """You are a literary analysis assistant specialized in character extraction and gender analysis.
            Your task is to analyze the chapter content and identify ONLY named characters (proper nouns) mentioned in it.
            
            Important rules:
            1. ONLY include characters with specific names (proper nouns)
            2. DO NOT include generic terms like "the elders", "neighbors", "villagers", "the crowd", etc.
            3. DO NOT include unnamed characters or generic roles
            4. If a character is referred to by a title (like "Doctor Smith" or "Professor Johnson"), include them
            5. If a character is referred to by a specific epithet (like "the tall man" or "the red-haired woman"), DO NOT include them unless they have a name
            
            For each named character, provide:
            1. A brief, one-line description that captures their essential nature or role
            2. Their gender (male, female, or unknown if not clear from context)
            
            Your response must be a valid JSON array of objects, where each object has:
            - name: The character's name (must be a proper noun)
            - description: A single-line description of the character's nature or role (max 100 characters)
            - gender: The character's gender (male, female, or unknown)
            
            Only include characters that are actually mentioned or appear in the chapter.
            Keep descriptions concise and focused on the character's core nature.
            If a character appears multiple times, combine their characteristics into a single entry.
            Analyze pronouns, titles, and context to determine gender when possible."""
        },
        {
            "role": "user",
            "content": f"""Chapter Title: {chapter.title}
            Chapter Content:
            {chapter.content}
            
            Please extract only the named characters from this chapter and provide their descriptions and gender."""
        }
    ]

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        try:
            # Extract the JSON object from the response
            response_text = response.choices[0].message.content
            # Clean up the response text to ensure it's valid JSON
            response_text = response_text.strip()
            
            # Parse the JSON
            characters_data = json.loads(response_text)
            
            # Validate the response structure
            if not isinstance(characters_data, dict):
                raise ValueError("Response must be a JSON object")
            
            if "characters" not in characters_data:
                raise ValueError("Response must contain a 'characters' array")
            
            if not isinstance(characters_data["characters"], list):
                raise ValueError("'characters' must be an array")
            
            # Process each character to add image URLs
            for char in characters_data["characters"]:
                if not isinstance(char, dict):
                    raise ValueError("Each character must be an object")
                
                if "name" not in char:
                    raise ValueError("Each character must have a name")
                
                if not isinstance(char["name"], str) or not char["name"].strip():
                    raise ValueError("Character name must be a non-empty string")
                
                if "description" not in char:
                    raise ValueError("Each character must have a description")
                
                if not isinstance(char["description"], str) or not char["description"].strip():
                    raise ValueError("Character description must be a non-empty string")
                
                if "gender" not in char:
                    raise ValueError("Each character must have a gender")
                
                if not isinstance(char["gender"], str) or not char["gender"].strip():
                    raise ValueError("Character gender must be a non-empty string")
                
                # Generate cartoon profile image URL based on gender
                gender = char["gender"].lower()
                if gender == "male":
                    char["image_url"] = "https://api.dicebear.com/7.x/adventurer/svg?seed=" + char["name"].replace(" ", "") + "&backgroundColor=b6e3f4"
                elif gender == "female":
                    char["image_url"] = "https://api.dicebear.com/7.x/adventurer/svg?seed=" + char["name"].replace(" ", "") + "&backgroundColor=ffd5dc"
                else:
                    char["image_url"] = "https://api.dicebear.com/7.x/adventurer/svg?seed=" + char["name"].replace(" ", "") + "&backgroundColor=c0aede"
            
            return ChapterCharactersResponse(**characters_data)
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse the AI response into proper JSON format: {str(e)}")
        except ValueError as e:
            # If the response doesn't match our schema, try to fix it with another API call
            retry_messages = messages + [
                {
                    "role": "assistant",
                    "content": response_text
                },
                {
                    "role": "user",
                    "content": """The previous response did not match the required format. Please provide a response in exactly this format:
                    {
                        "characters": [
                            {
                                "name": "Character Name",
                                "description": "Character's description and role in the chapter",
                                "gender": "male/female/unknown"
                            }
                        ]
                    }"""
                }
            ]
            
            try:
                retry_response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=retry_messages,
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                retry_text = retry_response.choices[0].message.content.strip()
                retry_data = json.loads(retry_text)
                
                # Validate the retry response
                if not isinstance(retry_data, dict) or "characters" not in retry_data:
                    raise Exception(f"Failed to generate a properly structured response after retry: {str(e)}")
                
                # Process each character to add image URLs
                for char in retry_data["characters"]:
                    gender = char["gender"].lower()
                    if gender == "male":
                        char["image_url"] = "https://api.dicebear.com/7.x/adventurer/svg?seed=" + char["name"].replace(" ", "") + "&backgroundColor=b6e3f4"
                    elif gender == "female":
                        char["image_url"] = "https://api.dicebear.com/7.x/adventurer/svg?seed=" + char["name"].replace(" ", "") + "&backgroundColor=ffd5dc"
                    else:
                        char["image_url"] = "https://api.dicebear.com/7.x/adventurer/svg?seed=" + char["name"].replace(" ", "") + "&backgroundColor=c0aede"
                
                return ChapterCharactersResponse(**retry_data)
                
            except Exception as retry_error:
                raise Exception(f"Failed to generate a valid response even after retry: {str(retry_error)}")
        except Exception as e:
            raise Exception(f"Error processing the response: {str(e)}")
            
    except Exception as e:
        raise Exception(str(e)) 