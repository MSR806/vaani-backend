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

# Add the project root to the Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Book
from app.services.ai_service import get_openai_client
from app.services.setting_service import get_setting_by_key
from .prompts.story_abstractor_prompts import (
    CHARACTER_ARC_SYSTEM_PROMPT,
    CHARACTER_ARC_USER_PROMPT_TEMPLATE,
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
    def __init__(self, book_id: int, db: Session = None):
        """Initialize the abstractor with a book ID and optional database session"""
        self.book_id = book_id
        self.db = db
        self.book = None
        
        # Set up input/output directories
        self.input_dir = INPUT_DIR / f"book_{book_id}"
        self.output_dir = self.input_dir / "template"
        
        # Input subdirectories for analysis results
        self.summaries_dir = self.input_dir / "analysis/summaries"
        self.plot_beats_dir = self.input_dir / "analysis/plot_beats"
        self.character_arcs_input_dir = self.input_dir / "analysis/character_arcs"
        
        # Output subdirectories for templates
        self.character_arcs_dir = self.output_dir / "character_arcs"
        self.narrative_skeleton_dir = self.output_dir / "narrative_skeleton"
        
        # Initialize AI client
        self.client = get_openai_client()
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.character_arcs_dir.mkdir(parents=True, exist_ok=True)
        self.narrative_skeleton_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Validate input directories and load book info if database session provided"""
        # Verify input directory exists
        if not self.input_dir.exists():
            raise ValueError(f"Input directory not found: {self.input_dir}")
        
        # Verify required subdirectories exist
        required_dirs = [
            self.character_arcs_input_dir,
            self.plot_beats_dir
        ]
        
        for directory in required_dirs:
            if not directory.exists():
                raise ValueError(f"Required directory not found: {directory}")
        
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
        repo = CharacterArcsRepository()
        arcs = repo.get_by_type_and_source_id('GENERATED', self.book_id)
        for arc in arcs:
            if arc.name and arc.content:
                character_arcs[arc.name] = arc.content
        return character_arcs
    
    
    async def read_plot_beats(self) -> List[Dict[str, Any]]:
        """Read all plot beats from the database and return their contents"""
        plot_beats = []
        repo = PlotBeatRepository()
        beats = repo.get_by_source_id(self.book_id, 'GENERATED')
        for beat in beats:
            if beat.content:
                plot_beats.append({"content": beat.content})
        return plot_beats
    
    
    async def abstract_character_arc(self, character_name: str, character_growth: str, template_id: int = None) -> Dict[str, Any]:
        """Transform a specific character's growth into a generalized arc structure and store it as TEMPLATE in DB"""
        repo = CharacterArcsRepository()
        # Check if already abstracted
        existing_arc = repo.get_by_name_type_and_source_id(character_name, 'TEMPLATE', template_id)
        if existing_arc:
            return {
                "original_character": character_name,
                "abstract_arc": existing_arc.content,
            }
        
        model, temperature = await self._get_model_settings("character_arc")
        system_prompt = CHARACTER_ARC_SYSTEM_PROMPT
        user_prompt = CHARACTER_ARC_USER_PROMPT_TEMPLATE.format(character_growth=character_growth)
        logger.info(f"Abstracting character arc for: {character_name}")
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
            abstract_content = abstract_content.replace('```markdown', '').replace('```', '')
                        
            # Use the first line as the archetype title without complex parsing
            lines = abstract_content.split('\n')
            archetype = lines[0] if lines else "Unknown Archetype"

            # Store in DB as TEMPLATE
            repo.create(
                content=abstract_content,
                type="TEMPLATE",
                source_id=template_id,
                name=character_name,
                archetype=archetype
            )
            return {
                "original_character": character_name,
                "abstract_arc": abstract_content,
                "archetype": archetype
            }
        except Exception as e:
            logger.error(f"Error abstracting character arc: {str(e)}")
            return {
                "original_character": character_name,
                "abstract_arc": f"# Character Arc Template\n\nCould not generate abstraction due to an error: {str(e)}",
            }
    
    async def abstract_all_character_arcs(self, template_id: int = None) -> Dict[str, Any]:
        """Abstract all character arcs into generalized templates"""
        logger.info("Abstracting all character arcs")
        character_arcs = await self.read_character_arcs()
        abstract_arcs = {}
        for character_name, arc_content in character_arcs.items():
            abstract_arc = await self.abstract_character_arc(character_name, arc_content, template_id)
            abstract_arcs[character_name] = abstract_arc
        return abstract_arcs
    
    async def abstract_plot_beats(self, plot_beats: List[Dict[str, Any]], template_id: int = None) -> List[Dict[str, Any]]:
        """Transform specific plot beats into a generalized narrative skeleton"""
        model, temperature = await self._get_model_settings("narrative_skeleton")
        
        # Get character mappings from the already abstracted character arcs
        character_mappings = {}
        if template_id is not None:
            repo = CharacterArcsRepository()
            character_arc_templates = repo.get_character_arc_templates_by_source_id(template_id)
            for arc in character_arc_templates:
                if arc.name and arc.archetype:
                    character_mappings[arc.name] = arc.archetype
            if character_mappings:
                logger.info(f"Found {len(character_mappings)} character mappings from DB")
        
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
                
                if template_id is not None:
                    repo = PlotBeatRepository()
                    repo.create(
                        content=abstract_content,
                        type="TEMPLATE",
                        source_id=template_id
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
        return abstract_beats
    
    async def run_abstraction(self) -> Dict[str, Any]:
        """Run the full abstraction pipeline"""
        logger.info(f"Starting abstraction process for book {self.book_id}")
        await self.initialize()
        # Create a new template in the DB with all statuses as NOT_STARTED
        template_repo = TemplateRepository()
        template = template_repo.create(
            name=f"Template for Book {self.book_id}",
            book_id=self.book_id,
            summary_status="NOT_STARTED",
            character_arc_status="NOT_STARTED",
            plot_beats_status="NOT_STARTED",
            character_arc_template_status="NOT_STARTED",
            plot_beat_template_status="NOT_STARTED"
        )
        template_id = template.id
        
        # Gather source data
        character_arcs = await self.read_character_arcs()
        plot_beats = await self.read_plot_beats()
        
        # Check if we have the necessary data
        if not character_arcs:
            logger.warning("No character arcs found")
        
        if not plot_beats:
            logger.warning("No plot beats found")
        
        # Run abstractions
        meta_data = {}
        
        # Step 1: Character Arcs
        if character_arcs:
            abstract_arcs = await self.abstract_all_character_arcs(template_id)
        
        # Step 2: Plot Beats
        if plot_beats:
            abstract_beats = await self.abstract_plot_beats(plot_beats, template_id)
        
        logger.info("Abstraction process completed")


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python plot_abstractor.py <book_id>")
        sys.exit(1)
        
    book_id = int(sys.argv[1])
    logger.info(f"Starting abstraction for book ID: {book_id}")
    
    # Get database session
    db = next(get_db())
    
    try:
        abstractor = StoryAbstractor(book_id, db)
        template_index = await abstractor.run_abstraction()
        logger.info(f"Template created successfully at: {abstractor.output_dir}")
        print(json.dumps(template_index, indent=2))
    except Exception as e:
        logger.error(f"Error during abstraction: {str(e)}")
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())