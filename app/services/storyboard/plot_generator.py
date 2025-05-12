#!/usr/bin/env python3
import logging
from sqlalchemy.orm import Session

# Import from app services
from app.services.ai_service import get_openai_client
from app.models.models import PlotBeat
from app.models.enums import StoryboardStatus
from app.repository.storyboard_repository import StoryboardRepository
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.plot_beat_repository import PlotBeatRepository
from app.services.setting_service import get_setting_by_key
from app.utils.constants import SettingKeys

# Import prompt templates
from prompts.story_generator_prompts import (
    PLOT_BEAT_SYSTEM_PROMPT,
    PLOT_BEAT_USER_PROMPT_TEMPLATE,
    PLOT_SUMMARY_SYSTEM_PROMPT,
    PLOT_SUMMARY_USER_PROMPT_TEMPLATE
)

logger = logging.getLogger(__name__)

class PlotBeatGenerator:
    def __init__(self, db: Session, storyboard_id: int):
        self.db = db
        self.storyboard_id = storyboard_id
        self.storyboard_repo = StoryboardRepository(self.db)
        self.character_arcs_repo = CharacterArcsRepository(self.db)
        self.plot_beats_repo = PlotBeatRepository(self.db)
        
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
            self.character_arcs = self.character_arcs_repo.get_by_type_and_source_id("STORYBOARD", self.storyboard_id)
            logger.info(f"Got {len(self.character_arcs)} character arcs")
            self.plot_beats_templates = self.plot_beats_repo.get_by_source_id_and_type(self.storyboard.template_id, "TEMPLATE")
            logger.info(f"Got {len(self.plot_beats_templates)} plot beat templates")
    

    async def generate_plot_beats(self, plot_beat_template: PlotBeat, previous_plot_beat=None, summary_till_now=None):
        character_content_str = ""
        for character_arc in self.character_arcs:
            character_content_str += f"### {character_arc.name}\n"
            character_content_str += f"{character_arc.content}\n\n"

        # Construct plot content based on what we have
        plot_till_now = ""
        
        # Add summary of earlier plot beats if available
        if summary_till_now:
            plot_till_now += f"## Summary of Previous Plot Beats\n\n{summary_till_now}\n\n"
        
        # Add the previous plot beat in full if available
        if previous_plot_beat:
            plot_till_now += f"## Previous Plot Beats: \n\n{previous_plot_beat.content}\n\n"

        try:
            system_prompt = PLOT_BEAT_SYSTEM_PROMPT
            user_prompt = PLOT_BEAT_USER_PROMPT_TEMPLATE.format(
                prompt=self.storyboard.prompt,
                character_content=character_content_str,
                plot_template=plot_beat_template.content,
                plot_till_now=plot_till_now
            )

            response = self.client.chat.completions.create(
                model=get_setting_by_key(self.db, SettingKeys.PLOT_BEAT_GENERATION_MODEL.value).value,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=float(get_setting_by_key(self.db, SettingKeys.PLOT_BEAT_GENERATION_TEMPERATURE.value).value),
            )

            return self.plot_beats_repo.create(response.choices[0].message.content, "STORYBOARD", self.storyboard_id)
        
        except Exception as e:
            logger.error(f"Error generating plot beat: {e}")
            return None
    
    async def summarize_plot_till_now(self):
        try:
            response = self.client.chat.completions.create(
                model=get_setting_by_key(self.db, SettingKeys.PLOT_SUMMARY_GENERATION_MODEL.value).value,
                temperature=float(get_setting_by_key(self.db, SettingKeys.PLOT_SUMMARY_GENERATION_TEMPERATURE.value).value),
                messages=[
                    {"role": "system", "content": PLOT_SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": PLOT_SUMMARY_USER_PROMPT_TEMPLATE.format(
                        plot_beats_till_now=self.plot_beats_till_now
                    )}
                ]
            )
            
            plot_summary = response.choices[0].message.content.strip()
            
            return plot_summary
        except Exception as e:
            logger.error(f"Error summarizing plot till now: {str(e)}")
            return None
    
    async def generate_all_plot_beats(self):
        # Initialize empty collections
        self.plot_beats = []
        self.plot_beats_till_now = ""
        current_summary = None
        previous_beat = None
        
        # Process plot beat templates one by one
        for i, plot_beat_template in enumerate(self.plot_beats_templates):
            logger.info(f"Generating plot beat {i+1}/{len(self.plot_beats_templates)}")
            
            # For the first beat, there's nothing before it
            if i == 0:
                plot_beat = await self.generate_plot_beats(plot_beat_template)
            
            # For the second beat, we have only the first beat but no summary yet
            elif i == 1:
                plot_beat = await self.generate_plot_beats(
                    plot_beat_template, 
                    previous_plot_beat=previous_beat
                )
            
            # For third beat onward, use summary of all beats up to n-2, and full content of n-1
            else:
                # Create plot beats collection for summarization (all beats up to n-2)
                beats_for_summary = self.plot_beats[:-1]  # Exclude the most recent beat
                beats_text = ""
                
                for j, beat in enumerate(beats_for_summary):
                    beats_text += f"## Plot Beat {j+1}:\n{beat.content}\n\n"
                
                # Generate summary of all beats up to n-2
                self.plot_beats_till_now = beats_text
                current_summary = await self.summarize_plot_till_now()
                
                # Generate the current beat using the summary and previous beat
                plot_beat = await self.generate_plot_beats(
                    plot_beat_template,
                    previous_plot_beat=previous_beat,
                    summary_till_now=current_summary
                )
            
            # Add the new beat to our collection
            if plot_beat:
                self.plot_beats.append(plot_beat)
                previous_beat = plot_beat
                logger.info(f"Successfully generated plot beat")
            else:
                logger.error(f"Failed to generate plot beat for template")
        
    
    async def execute(self):
        await self.initialize()
        
        self.storyboard_repo.update(self.storyboard_id, status=StoryboardStatus.PLOT_BEATS_GENERATION_IN_PROGRESS)
        
        await self.generate_all_plot_beats()
        
        self.storyboard_repo.update(self.storyboard_id, status=StoryboardStatus.PLOT_BEATS_GENERATION_COMPLETED)
        
        logger.info(f"Plot beat generation completed. Generated {len(self.plot_beats)} plot beats.")
