#!/usr/bin/env python3
import asyncio
import json
import logging
import re
import traceback

from sqlalchemy.orm import Session

from app.models.enums import StoryboardStatus

# Import prompt templates
from app.prompts.story_generator_prompts import CHARACTER_NAME_GENERATION_PROMPT
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.storyboard_repository import StoryboardRepository
from app.schemas.character_arcs import CharacterArcContentJSON

# Import from app services
from app.services.ai_service import get_openai_client
from app.utils.model_settings import ModelSettings
from app.utils.story_generator_utils import process_character_arcs

logger = logging.getLogger(__name__)


class CharacterArcGenerator:
    def __init__(self, db: Session, storyboard_id: int):
        """Initialize the character arc generator with a book ID"""
        self.db = db
        self.storyboard_id = storyboard_id
        self.character_arc_repo = CharacterArcsRepository(self.db)
        self.storyboard_repo = StoryboardRepository(self.db)
        self.model_settings = ModelSettings(self.db)

        # Initialize AI client
        try:
            self.client = get_openai_client()
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI client: {str(e)}")
            self.client = None

    async def initialize(self):
        """Initialize templates and directories"""
        # Verify book template directory exists
        if self.storyboard_id:
            self.storyboard = self.storyboard_repo.get_by_id(self.storyboard_id)

        if self.storyboard:
            self.character_arc_templates = self.character_arc_repo.get_by_type_and_source_id(
                "TEMPLATE", self.storyboard.template_id
            )

    async def generate_character_names(self):
        """Generate character names using the AI client"""
        character_template_names = []
        for character_arc in self.character_arc_templates:
            logger.info(f"Processing character arc: {character_arc.archetype}")
            content_json = CharacterArcContentJSON(**character_arc.content_json)
            character_template_names.append(
                {
                    "name": character_arc.archetype,
                    "role": character_arc.role,
                    "blood_relations": content_json.blood_relations,
                    "gender_age": content_json.gender_age,
                    "description": content_json.description,
                }
            )

        if not character_template_names:
            logger.warning("No character templates found")
            return {}

        # Format the character templates for the prompt
        template_strings = []
        for char in character_template_names:
            template_str = f"{char['name']}:\n"
            template_str += f"Role: {char['role']}\n"
            template_str += f"Gender and age: {char['gender_age']}\n"
            template_str += f"Description: {char['description']}\n"
            template_strings.append(template_str)

        # Get the story prompt from the storyboard
        story_prompt = (
            self.storyboard.prompt
            if hasattr(self, "storyboard") and self.storyboard
            else "Generate character names appropriate for a Billionare romance genre for web fiction."
        )

        # Prepare the prompt with all character templates
        prompt = CHARACTER_NAME_GENERATION_PROMPT.format(
            character_templates="\n\n".join(template_strings), prompt=story_prompt
        )

        try:
            model, temperature = self.model_settings.character_arc_generation()
            client = get_openai_client(model)

            # Call the AI model in a separate thread to avoid blocking the event loop
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a creative writer's assistant who creates realistic character names based on character descriptions.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )

            name_mappings = response.choices[0].message.content.strip()

            logger.info(f"Generated character names: {name_mappings}")
            return name_mappings

        except Exception as e:
            logger.error(f"Error generating character names: {str(e)} {traceback.format_exc()}")
            return {}

    async def generate_character_arcs(self):
        """Generate character arcs using the AI client"""
        if not self.client:
            raise ValueError("AI client not initialized")

        try:
            # Get model and temperature from settings
            model, temperature = self.model_settings.character_arc_generation()
            client = get_openai_client(model)

            # Get character name mappings as string
            character_names_string = await self.generate_character_names()

            if not character_names_string:
                logger.error("No character names generated")
                return

            logger.info(f"Generated character names: {character_names_string}")

            # Process character arcs using the utility function - pass the raw string
            character_arcs = await process_character_arcs(
                character_templates=self.character_arc_templates,
                character_mappings=character_names_string,  # Updated parameter name
                story_prompt=self.storyboard.prompt,
                client=client,
                model=model,
                temperature=temperature,
            )

            # Save all character arcs to the database
            if character_arcs:
                # Convert CharacterArc objects to dictionaries for database storage
                character_arcs_data = [
                    {
                        "name": arc.name,
                        "role": arc.role,
                        "type": "STORYBOARD",
                        "archetype": arc.archetype,
                        "source_id": self.storyboard_id,
                        "content_json": arc.content_json.model_dump(),
                    }
                    for arc in character_arcs
                ]

                self.character_arc_repo.batch_create(character_arcs_data)
                logger.info(f"Stored {len(character_arcs_data)} character arcs in batch operation")
            else:
                logger.error("No character arcs generated")

        except Exception as e:
            logger.error(f"Error generating character arcs: {str(e)} {traceback.format_exc()}")

        logger.info("Character arc generation completed")

    async def execute(self):
        await self.initialize()

        self.storyboard_repo.update(
            self.storyboard_id, status=StoryboardStatus.CHARACTER_ARC_GENERATION_IN_PROGRESS
        )

        await self.generate_character_arcs()

        self.storyboard_repo.update(
            self.storyboard_id, status=StoryboardStatus.CHARACTER_ARC_GENERATION_COMPLETED
        )

        logger.info(f"Character arc generation completed.")
