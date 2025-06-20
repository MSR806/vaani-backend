#!/usr/bin/env python3
import asyncio
import logging
from typing import List

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.enums import StoryboardStatus
from app.models.models import PlotBeat

# Import prompt templates
from app.prompts.story_generator_prompts import (
    CHARACTER_IDENTIFICATION_SYSTEM_PROMPT,
    CHARACTER_IDENTIFICATION_USER_PROMPT_TEMPLATE,
    PLOT_BEAT_SYSTEM_PROMPT,
    PLOT_BEAT_USER_PROMPT_TEMPLATE,
)
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.plot_beat_repository import PlotBeatRepository
from app.repository.storyboard_repository import StoryboardRepository

# Import from app services
from app.services.ai_service import get_openai_client
from app.utils.model_settings import ModelSettings
from app.utils.story_generator_utils import get_character_arcs_content_by_chapter_id

logger = logging.getLogger(__name__)


class CharacterIdentificationResponse(BaseModel):
    character_ids: List[int]


class PlotBeatGenerator:
    def __init__(self, db: Session, storyboard_id: int):
        self.db = db
        self.storyboard_id = storyboard_id
        self.storyboard_repo = StoryboardRepository(self.db)
        self.character_arcs_repo = CharacterArcsRepository(self.db)
        self.plot_beats_repo = PlotBeatRepository(self.db)
        self.model_settings = ModelSettings(self.db)

        # Initialize AI client
        try:
            self.client = get_openai_client()
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI client: {str(e)}")
            self.client = None

    async def initialize(self):
        if self.storyboard_id:
            self.storyboard = self.storyboard_repo.get_by_id(self.storyboard_id)

        if self.storyboard:
            self.character_arcs = self.character_arcs_repo.get_by_type_and_source_id(
                "STORYBOARD", self.storyboard_id
            )
            logger.info(f"Got {len(self.character_arcs)} character arcs")
            # Get plot beat templates and sort them by ID
            templates = self.plot_beats_repo.get_by_source_id_and_type(
                self.storyboard.template_id, "TEMPLATE"
            )
            self.plot_beats_templates = sorted(templates, key=lambda x: x.id)
            logger.info(f"Got {len(self.plot_beats_templates)} plot beat templates")

    async def identify_characters_in_plot_beat(self, plot_beat: PlotBeat) -> List[int]:
        try:
            # Build character list with IDs
            character_list = ""
            for character_arc in self.character_arcs:
                character_list += f"Character ID: {character_arc.id}, Name: {character_arc.name}\n"

            system_prompt = CHARACTER_IDENTIFICATION_SYSTEM_PROMPT
            user_prompt = CHARACTER_IDENTIFICATION_USER_PROMPT_TEMPLATE.format(
                character_list_with_ids=character_list, plot_beat_content=plot_beat.content
            )
            model, temperature = self.model_settings.character_identification()
            client = get_openai_client(model)

            # Use asyncio.to_thread for this synchronous call as well
            completion = await asyncio.to_thread(
                client.beta.chat.completions.parse,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                response_format=CharacterIdentificationResponse,
            )

            return completion.choices[0].message.parsed.character_ids

        except Exception as e:
            logger.error(f"Error identifying characters in plot beat: {e}")
            return []

    async def generate_plot_beat(self, plot_beat_template: PlotBeat, chapter_id: int):
        import re

        # Extract character pattern references (char_x) from plot template
        char_pattern = r"char_\d+"
        mentioned_chars = set(re.findall(char_pattern, plot_beat_template.content))
        logger.info(f"Characters mentioned in plot template: {mentioned_chars}")

        # Create mapping between char_x archetypes and character names and format for prompt
        character_mapping_str = ""

        for character_arc in self.character_arcs:
            if character_arc.archetype and character_arc.archetype in mentioned_chars:
                character_mapping_str += f"{character_arc.archetype} = {character_arc.name}\n"

        logger.info(f"Character mappings: {character_mapping_str}")

        # Build character content string
        character_content_str = ""
        character_arcs_content = get_character_arcs_content_by_chapter_id(
            self.character_arcs, chapter_id, mentioned_chars
        )
        logger.info(
            f"Plot beat chapter {chapter_id} character arcs content: {', '.join([character_arc[0] for character_arc in character_arcs_content])}"
        )
        for character_arc_name, character_arc_content, _ in character_arcs_content:
            character_content_str += f"### {character_arc_name}\n"
            character_content_str += f"{character_arc_content}\n\n"

        try:
            system_prompt = PLOT_BEAT_SYSTEM_PROMPT
            user_prompt = PLOT_BEAT_USER_PROMPT_TEMPLATE.format(
                prompt=self.storyboard.prompt,
                character_content=character_content_str,
                plot_template=plot_beat_template.content,
                character_mappings=character_mapping_str,
            )
            model, temperature = self.model_settings.plot_beat_generation()
            client = get_openai_client(model)

            # Run synchronous OpenAI call in a separate thread to avoid blocking the event loop
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )

            # Instead of saving to DB here, just return the content and metadata
            content = response.choices[0].message.content

            # Get character IDs without creating a plot beat first
            # We'll create a temporary plot beat object just for identification
            temp_plot_beat = PlotBeat(content=content)
            character_ids = await self.identify_characters_in_plot_beat(temp_plot_beat)

            # Return a dict with all the data needed to create the plot beat later
            return {"content": content, "character_ids": character_ids, "chapter_id": chapter_id}

        except Exception as e:
            error_message = f"Error generating plot beat: {e}"
            logger.error(error_message)
            # Return a dict with error information instead of None
            return {
                "content": f"Error generating plot beat: {e}",
                "character_ids": [],
                "chapter_id": chapter_id,
                "error": True,
            }

    async def generate_all_plot_beats(self):
        self.plot_beats = []
        semaphore = asyncio.Semaphore(15)  # Limit to 15 concurrent tasks

        async def generate_with_semaphore(i, plot_beat_template):
            async with semaphore:
                logger.info(f"Generating plot beat {i+1}/{len(self.plot_beats_templates)}")
                plot_beat_data = await self.generate_plot_beat(plot_beat_template, i + 1)
                logger.info(f"Completed plot beat {i+1}")

                # Return index along with data to maintain original order
                return (i, plot_beat_data)

        # Create all tasks
        tasks = [
            generate_with_semaphore(i, template)
            for i, template in enumerate(self.plot_beats_templates)
        ]

        # Execute tasks concurrently with semaphore control
        results = await asyncio.gather(*tasks)

        # Since we're no longer returning None, we can just sort all results by index
        sorted_results = sorted(results, key=lambda x: x[0])

        # Prepare data for batch creation
        logger.info(f"Preparing {len(results)} plot beats for batch creation...")
        batch_items = []

        for _, plot_beat_data in sorted_results:
            batch_items.append(
                {
                    "content": plot_beat_data["content"],
                    "type": "STORYBOARD",
                    "source_id": self.storyboard_id,
                    "character_ids": plot_beat_data["character_ids"],
                }
            )

        # Save all plot beats in a single transaction
        logger.info(f"Batch creating {len(batch_items)} plot beats...")
        created_plot_beats = self.plot_beats_repo.batch_create(batch_items)

        self.plot_beats = created_plot_beats

        logger.info(f"Successfully saved {len(self.plot_beats)} plot beats in proper order")

    async def execute(self):
        await self.initialize()

        self.storyboard_repo.update(
            self.storyboard_id, status=StoryboardStatus.PLOT_BEATS_GENERATION_IN_PROGRESS
        )

        await self.generate_all_plot_beats()

        self.storyboard_repo.update(
            self.storyboard_id, status=StoryboardStatus.PLOT_BEATS_GENERATION_COMPLETED
        )

        logger.info(f"Plot beat generation completed. Generated {len(self.plot_beats)} plot beats.")
