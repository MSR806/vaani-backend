#!/usr/bin/env python3
import os
import sys
import json
import time
import re
import asyncio
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from app.schemas.schemas import TemplateStatusEnum

# Add the project root to the Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Book
from app.services.ai_service import get_openai_client
from app.services.setting_service import get_setting_by_key
from prompts.story_abstractor_prompts import (
    CHARACTER_ARC_SYSTEM_PROMPT,
    CHARACTER_ARC_USER_PROMPT_TEMPLATE,
    CHARACTER_ARC_BATCH_USER_PROMPT_TEMPLATE,
    PLOT_BEATS_SYSTEM_PROMPT,
    PLOT_BEATS_USER_PROMPT_TEMPLATE,
)
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.plot_beat_repository import PlotBeatRepository
from app.repository.template_repository import TemplateRepository

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
INPUT_DIR = Path(__file__).parent / "output"

# Hardcoded AI model settings
CHARACTER_MODEL = "gpt-4o"      # For character arcs (better quality)
PLOT_MODEL = "gpt-4o"          # For narrative skeleton (better quality)

# Temperature settings
CHARACTER_TEMPERATURE = 0.2
PLOT_TEMPERATURE = 0.4


class StoryAbstractor:
    def __init__(self, book_id: int, db: Session = None, template_id: int = None):
        """Initialize the abstractor with a book ID and optional database session"""
        self.book_id = book_id
        self.db = db
        self.book = None
        self.template_id = template_id
        self.template_repo = TemplateRepository(self.db)
        
        # Initialize AI client
        self.client = get_openai_client()
    
    async def initialize(self):
        """Validate input directories and load book info if database session provided"""
        
        # If database session provided, load book info
        if self.db:
            self.book = self.db.query(Book).filter(Book.id == self.book_id).first()
            if not self.book:
                raise ValueError(f"Book with ID {self.book_id} not found")
            
            logger.info(f"Loaded book: {self.book.title}")
        
        logger.info(f"Initialized StoryAbstractor for book {self.book_id}")
        
        return True
    
    async def _get_model_settings(self, abstraction_type: str):
        """Get AI model settings based on abstraction type"""
        # First try database settings, then fall back to hardcoded defaults
        try:
            # Try to get settings from database based on abstraction type
            setting_key_prefix = f"story_abstractor_{abstraction_type.lower()}"
            model = get_setting_by_key(f"{setting_key_prefix}_model")
            temp = get_setting_by_key(f"{setting_key_prefix}_temperature")
            
            if model and temp:
                return model, float(temp)
        except:
            # If any error occurs, use hardcoded settings
            pass
            
        # Use hardcoded settings based on abstraction type
        if abstraction_type == "character_arc":
            return CHARACTER_MODEL, CHARACTER_TEMPERATURE
        elif abstraction_type == "narrative_skeleton":
            return PLOT_MODEL, PLOT_TEMPERATURE
        else:
            # Default to highest quality model if type not recognized
            return "gpt-4o", 0.3
    
    async def read_character_arcs(self) -> Dict[str, str]:
        """Read all character arcs from the database and return their contents"""
        character_arcs = {}
        repo = CharacterArcsRepository(self.db)
        arcs = repo.get_by_type_and_source_id('EXTRACTED', self.book_id)
        for arc in arcs:
            if arc.name and arc.content:
                character_arcs[arc.name] = arc.content
        return character_arcs
    
    
    async def read_plot_beats(self) -> List[Dict[str, Any]]:
        """Read all plot beats from the database and return their contents"""
        plot_beats = []
        repo = PlotBeatRepository(self.db)
        beats = repo.get_by_source_id_and_type(self.book_id, 'EXTRACTED')
        for beat in beats:
            if beat.content:
                plot_beats.append({"content": beat.content})
        return plot_beats
    
    
    async def abstract_character_arcs_batch(self, character_arcs: Dict[str, str]) -> Dict[str, Any]:
        """Batch transform all character arcs into generalized templates using a single AI call."""
        repo = CharacterArcsRepository(self.db)
        # Check for already abstracted arcs
        existing_arcs = repo.get_by_type_and_source_id('TEMPLATE', self.template_id)
        existing_names = {arc.name for arc in existing_arcs}
        arcs_to_abstract = {name: content for name, content in character_arcs.items() if name not in existing_names}
        results = {}
        # If all arcs are already abstracted, return them
        if not arcs_to_abstract:
            for arc in existing_arcs:
                results[arc.name] = {
                    "original_character": arc.name,
                    "abstract_arc": arc.content,
                    "archetype": arc.archetype or "Unknown Archetype"
                }
            return results
        # Prepare batch prompt
        batch_text = ""
        for name, content in arcs_to_abstract.items():
            batch_text += f"CHARACTER: {name}\nFILE_START\n{content}\nFILE_END\n\n"
        model, temperature = await self._get_model_settings("character_arc")
        system_prompt = CHARACTER_ARC_SYSTEM_PROMPT
        user_prompt = CHARACTER_ARC_BATCH_USER_PROMPT_TEMPLATE.format(character_growth_batch=batch_text)
        logger.info(f"Batch abstracting {len(arcs_to_abstract)} character arcs")
        logger.info(f"Using model: {model}, temperature: {temperature}")
        try:
            response = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            output = response.choices[0].message.content.strip()
            # Parse output
            pattern = r"CHARACTER: (.*?)\nFILE_START\n(.*?)\nFILE_END"
            matches = re.findall(pattern, output, re.DOTALL)
            input_names = list(arcs_to_abstract.keys())
            used_names = set()
            for idx, (name, abstract_content) in enumerate(matches):
                # Always use the original input name by order
                if idx < len(input_names):
                    original_name = input_names[idx]
                    if name.strip() != original_name:
                        logger.warning(f"Model output name '{name.strip()}' does not match input '{original_name}'. Using input name.")
                else:
                    original_name = name.strip()
                    logger.warning(f"Model output name '{name.strip()}' could not be matched by order; using as is.")

                # Extract archetype and role from the first line
                lines = abstract_content.strip().split('\n')
                archetype = "Unknown Archetype"
                role = "Unknown Role"
                for line in lines:
                    match = re.match(r"# ([^-]+) - ([^-]+)", line)
                    if match:
                        role = match.group(1).strip()
                        archetype = match.group(2).strip()
                        break

                repo.create(
                    content=abstract_content.strip(),
                    type="TEMPLATE",
                    source_id=self.template_id,
                    name=original_name,
                    archetype=archetype,
                    role=role
                )
                results[original_name] = {
                    "original_character": original_name,
                    "abstract_arc": abstract_content.strip(),
                    "archetype": archetype,
                    "role": role
                }
            # Add already existing arcs
            for arc in existing_arcs:
                if arc.name not in results:
                    results[arc.name] = {
                        "original_character": arc.name,
                        "abstract_arc": arc.content,
                        "archetype": arc.archetype or "Unknown Archetype"
                    }
            return results
        except Exception as e:
            logger.error(f"Error batch abstracting character arcs: {str(e)}")
            # Return error for all arcs
            for name in arcs_to_abstract:
                results[name] = {
                    "original_character": name,
                    "abstract_arc": f"# Character Arc Template\n\nCould not generate abstraction due to an error: {str(e)}",
                }
            return results
    
    async def abstract_all_character_arcs(self) -> Dict[str, Any]:
        """Abstract all character arcs into generalized templates using batch abstraction."""
        logger.info("Abstracting all character arcs (batch mode)")
        self.template_repo.update_character_arc_template_status(self.template_id, TemplateStatusEnum.IN_PROGRESS)
        character_arcs = await self.read_character_arcs()
        abstract_arcs = await self.abstract_character_arcs_batch(character_arcs)
        self.template_repo.update_character_arc_template_status(self.template_id, TemplateStatusEnum.COMPLETED)
        return abstract_arcs
    
    async def abstract_plot_beats(self, plot_beats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform specific plot beats into a generalized narrative skeleton"""
        model, temperature = await self._get_model_settings("narrative_skeleton")
        
        # Get character mappings from the already abstracted character arcs
        character_mappings = {}
        if self.template_id is not None:
            repo = CharacterArcsRepository(self.db)
            character_arc_templates = repo.get_by_type_and_source_id('TEMPLATE', self.template_id)
            for arc in character_arc_templates:
                if arc.name and arc.archetype:
                    character_mappings[arc.name] = arc.archetype
            if character_mappings:
                logger.info(f"Found {len(character_mappings)} character mappings from DB")


        self.template_repo.update_plot_beat_template_status(self.template_id, TemplateStatusEnum.IN_PROGRESS)
        abstract_beats = []
        
        for beat_data in plot_beats:
            content = beat_data["content"]
            system_prompt = PLOT_BEATS_SYSTEM_PROMPT
            # Prepare character mapping information if available
            character_map_text = ""
            if character_mappings:
                character_map_text = "\nUse these character archetype mappings when replacing character names:\n"
                for original, archetype in character_mappings.items():
                    character_map_text += f"- {original} → {archetype}\n"
            user_prompt = PLOT_BEATS_USER_PROMPT_TEMPLATE.format(content=content, character_map_text=character_map_text)
            logger.info(f"Abstracting plot beats")
            logger.info(f"Using model: {model}, temperature: {temperature}")
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                abstract_content = response.choices[0].message.content.strip()
                
                if self.template_id is not None:
                    repo = PlotBeatRepository(self.db)
                    repo.create(
                        content=abstract_content,
                        type="TEMPLATE",
                        source_id=self.template_id
                    )
                abstract_beats.append({
                    "abstract_content": abstract_content
                })
            except Exception as e:
                logger.error(f"Error abstracting plot beats: {str(e)}") 
                
                # Create an error message as the content
                error_content = f"# Narrative Skeleton\n\nCould not generate abstraction due to an error: {str(e)}"
                
                abstract_beats.append({
                    "abstract_content": error_content,
                    "error": str(e)
                })
                self.template_repo.update_plot_beat_template_status(self.template_id, TemplateStatusEnum.FAILED)
        self.template_repo.update_plot_beat_template_status(self.template_id, TemplateStatusEnum.COMPLETED)
        return abstract_beats
    
    async def run_abstraction(self) -> Dict[str, Any]:
        """Run the full abstraction pipeline"""
        logger.info(f"Starting abstraction process for book {self.book_id}")
        await self.initialize()
        
        # Gather source data
        character_arcs = await self.read_character_arcs()
        plot_beats = await self.read_plot_beats()
        
        # Check if we have the necessary data
        if not character_arcs:
            logger.warning("No character arcs found")
        
        if not plot_beats:
            logger.warning("No plot beats found")
        
        # Step 1: Character Arcs
        if character_arcs:
            abstract_arcs = await self.abstract_all_character_arcs()
        
        # Step 2: Plot Beats
        if plot_beats:
            abstract_beats = await self.abstract_plot_beats(plot_beats)
        
        logger.info("Abstraction process completed")
