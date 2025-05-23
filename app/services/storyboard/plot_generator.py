#!/usr/bin/env python3
import logging
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

# Import from app services
from app.services.ai_service import get_openai_client
from app.models.models import PlotBeat
from app.models.enums import StoryboardStatus
from app.repository.storyboard_repository import StoryboardRepository
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.plot_beat_repository import PlotBeatRepository
from app.services.setting_service import get_setting_by_key
from app.utils.constants import SettingKeys
from app.utils.model_settings import ModelSettings
# Import prompt templates
from prompts.story_generator_prompts import (
    PLOT_BEAT_SYSTEM_PROMPT,
    PLOT_BEAT_USER_PROMPT_TEMPLATE,
    CHARACTER_IDENTIFICATION_SYSTEM_PROMPT,
    CHARACTER_IDENTIFICATION_USER_PROMPT_TEMPLATE
)

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
        """Initialize templates and directories"""
        if self.storyboard_id:
            self.storyboard = self.storyboard_repo.get_by_id(self.storyboard_id)
        
        if self.storyboard:
            self.character_arcs = self.character_arcs_repo.get_by_type_and_source_id("STORYBOARD", self.storyboard_id)
            logger.info(f"Got {len(self.character_arcs)} character arcs")
            # Get plot beat templates and sort them by ID
            templates = self.plot_beats_repo.get_by_source_id_and_type(self.storyboard.template_id, "TEMPLATE")
            self.plot_beats_templates = sorted(templates, key=lambda x: x.id)
            logger.info(f"Got {len(self.plot_beats_templates)} plot beat templates")

    async def identify_characters_in_plot_beat(self, plot_beat: PlotBeat) -> List[int]:
        """Identify characters involved in a plot beat"""
        try:
            # Build character list with IDs
            character_list = ""
            for character_arc in self.character_arcs:
                character_list += f"Character ID: {character_arc.id}, Name: {character_arc.name}\n"

            system_prompt = CHARACTER_IDENTIFICATION_SYSTEM_PROMPT
            user_prompt = CHARACTER_IDENTIFICATION_USER_PROMPT_TEMPLATE.format(
                character_list_with_ids=character_list,
                plot_beat_content=plot_beat.content
            )
            model, temperature = self.model_settings.character_identification()
            client = get_openai_client(model)

            completion = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                response_format=CharacterIdentificationResponse,
            )

            return completion.choices[0].message.parsed.character_ids

        except Exception as e:
            logger.error(f"Error identifying characters in plot beat: {e}")
            return []

    async def generate_plot_beat(self, plot_beat_template: PlotBeat):
        """Generate a single plot beat by adapting the template to our story"""
        # Build character content string
        character_content_str = ""
        for character_arc in self.character_arcs:
            character_content_str += f"### {character_arc.name}\n"
            character_content_str += f"{character_arc.content}\n\n"

        try:
            system_prompt = PLOT_BEAT_SYSTEM_PROMPT
            user_prompt = PLOT_BEAT_USER_PROMPT_TEMPLATE.format(
                prompt=self.storyboard.prompt,
                character_content=character_content_str,
                plot_template=plot_beat_template.content
            )
            model, temperature = self.model_settings.plot_beat_generation()
            client = get_openai_client(model)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
            )

            plot_beat = self.plot_beats_repo.create(response.choices[0].message.content, "STORYBOARD", self.storyboard_id)
            
            # Identify characters in the plot beat
            if plot_beat:
                character_ids = await self.identify_characters_in_plot_beat(plot_beat)
                # Update plot beat with character IDs
                self.plot_beats_repo.update(plot_beat.id, {"character_ids": character_ids})
            
            return plot_beat
        
        except Exception as e:
            logger.error(f"Error generating plot beat: {e}")
            return None
    
    async def generate_all_plot_beats(self):
        """Generate all plot beats by adapting each template"""
        self.plot_beats = []
        
        # Process each plot beat template
        for i, plot_beat_template in enumerate(self.plot_beats_templates):
            logger.info(f"Generating plot beat {i+1}/{len(self.plot_beats_templates)}")
            
            plot_beat = await self.generate_plot_beat(plot_beat_template)
            
            if plot_beat:
                self.plot_beats.append(plot_beat)
                logger.info(f"Successfully generated plot beat")
            else:
                logger.error(f"Failed to generate plot beat for template")
    
    async def execute(self):
        """Execute the plot beat generation process"""
        await self.initialize()
        
        self.storyboard_repo.update(self.storyboard_id, status=StoryboardStatus.PLOT_BEATS_GENERATION_IN_PROGRESS)
        
        await self.generate_all_plot_beats()
        
        self.storyboard_repo.update(self.storyboard_id, status=StoryboardStatus.PLOT_BEATS_GENERATION_COMPLETED)
        
        logger.info(f"Plot beat generation completed. Generated {len(self.plot_beats)} plot beats.")
