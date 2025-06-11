#!/usr/bin/env python3
import json
from typing import List, Dict, Any
import logging

from app.schemas.schemas import TemplateStatusEnum
from sqlalchemy.orm import Session
from app.models.models import Book
from app.services.ai_service import get_openai_client
from app.utils.model_settings import ModelSettings
from app.prompts.story_abstractor_prompts import (
    PLOT_BEATS_SYSTEM_PROMPT,
    PLOT_BEATS_USER_PROMPT_TEMPLATE,
)
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.plot_beat_repository import PlotBeatRepository
from app.repository.template_repository import TemplateRepository
from app.utils.story_abstractor_utils import process_character_abstractions
from app.schemas.character_arcs import CharacterArc, CharacterArcContent
from app.models.models import CharacterArc as CharacterArcModel

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StoryAbstractor:
    def __init__(self, book_id: int, db: Session = None, template_id: int = None):
        """Initialize the abstractor with a book ID and optional database session"""
        self.book_id = book_id
        self.db = db
        self.book = None
        self.template_id = template_id
        self.template_repo = TemplateRepository(self.db)
        self.model_settings = None
        
        # Initialize AI client
        self.client = get_openai_client()
    
    async def initialize(self):
        """Validate input directories and load book info if database session provided"""
        
        # If database session provided, load book info
        if self.db:
            self.book = self.db.query(Book).filter(Book.id == self.book_id).first()
            if not self.book:
                raise ValueError(f"Book with ID {self.book_id} not found")
            
            # Initialize model settings
            self.model_settings = ModelSettings(self.db)
            logger.info("Initialized model settings")
            
            logger.info(f"Loaded book: {self.book.title}")
        
        logger.info(f"Initialized StoryAbstractor for book {self.book_id}")
        
        return True
    
    # Method removed and replaced with direct ModelSettings usage
    
    async def read_character_arcs(self) -> List[CharacterArcModel]:
        """Read all character arcs from the database and return their contents"""
        repo = CharacterArcsRepository(self.db)
        arcs = repo.get_by_type_and_source_id('EXTRACTED', self.book_id)
        return arcs
    
    
    async def read_plot_beats(self) -> List[Dict[str, Any]]:
        """Read all plot beats from the database and return their contents"""
        plot_beats = []
        repo = PlotBeatRepository(self.db)
        beats = repo.get_by_source_id_and_type(self.book_id, 'EXTRACTED')
        # Sort beats by ID in ascending order (from lowest to highest)
        beats = sorted(beats, key=lambda x: x.id, reverse=False)
        for beat in beats:
            if beat.content:
                plot_beats.append({"content": beat.content})
        return plot_beats
    
    
    async def abstract_character_arcs(self, character_arcs: List[CharacterArcModel]):
        repo = CharacterArcsRepository(self.db)
        existing_arcs = repo.get_by_type_and_source_id('TEMPLATE', self.template_id)
        if existing_arcs:
            logger.info(f"Found {len(existing_arcs)} existing character arcs")
            return
        
        character_arc_objects = []
        for arc in character_arcs:
            character_arc_objects.append(CharacterArc(name=arc.name, role=arc.role, content_json=[CharacterArcContent(**json.loads(item)) for item in arc.content_json]))
            
        logger.info(f"Async abstracting {len(character_arcs)} character arcs")
        
        model, temperature = self.model_settings.character_arc_template()
        try:
            # Use the new process_character_abstractions utility function
            abstraction_results = await process_character_abstractions(
                character_arc_objects, 
                self.client, 
                model, 
                temperature
            )
            
            # Save the abstracted character arcs to the database
            character_abstractions = abstraction_results
            
            # Convert results to match the expected output format of this function
            results = {}
            for abstraction in character_abstractions:
                # Convert content_json to string if it's not already
                name = abstraction.get("name", "") # original_name of the character arc
                content_json = abstraction.get("content_json", [])
                archetype = abstraction.get("abstract_name", "") # abstract_name of the character arc
                role = ""

                # Extract role if available from the first segment
                if content_json:
                    # Check the first segment for a role line
                    first_segment = content_json[0]
                    content = first_segment.get("content", "")
                    lines = content.split("\n")
                    for line in lines:
                        if line.startswith("# ") and " - " in line:
                            role = line.split(" - ")[0][2:].strip()
                            break
                
                # Save to database
                repo.create(
                    name=name,
                    type="TEMPLATE",
                    source_id=self.template_id,
                    content_json=json.dumps(content_json),
                    role=role,
                    archetype=archetype
                )
            
        except Exception as e:
            logger.error(f"Error abstracting character arcs: {str(e)}")
            # Return error for all arcs
            results = {}
            for name in arcs_to_abstract:
                results[name] = {
                    "original_character": name,
                    "abstract_arc": f"# Character Arc Template\n\nCould not generate abstraction due to an error: {str(e)}",
                    "error": str(e)
                }
            return results
    
    async def abstract_all_character_arcs(self):
        logger.info("Abstracting all character arcs (batch mode)")
        self.template_repo.update_character_arc_template_status(self.template_id, TemplateStatusEnum.IN_PROGRESS)
        character_arcs = await self.read_character_arcs()
        await self.abstract_character_arcs(character_arcs)
        self.template_repo.update_character_arc_template_status(self.template_id, TemplateStatusEnum.COMPLETED)
    
    async def abstract_plot_beats(self, plot_beats: List[Dict[str, Any]]):
        import asyncio
        
        # Constants
        MAX_CONCURRENT_TASKS = 15  # Limit concurrent API calls
        
        model, temperature = self.model_settings.plot_beats_template()
        
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

        # Prepare character mapping information if available
        character_map_text = ""
        if character_mappings:
            character_map_text = "\nUse these character archetype mappings when replacing character names:\n"
            for original, archetype in character_mappings.items():
                character_map_text += f"- {original} → {archetype}\n"
        logger.info(f"Character mapping text: {character_map_text}")

        self.template_repo.update_plot_beat_template_status(self.template_id, TemplateStatusEnum.IN_PROGRESS)
        
        # Create a semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        
        # Helper function to process a single plot beat with semaphore-controlled concurrency
        async def process_beat(beat_index, beat_data):
            async with semaphore:
                content = beat_data["content"]
                system_prompt = PLOT_BEATS_SYSTEM_PROMPT
                user_prompt = PLOT_BEATS_USER_PROMPT_TEMPLATE.format(content=content, character_map_text=character_map_text)
                logger.info(f"Abstracting plot beat {beat_index+1}/{len(plot_beats)} asynchronously")
                try:
                    # Note: OpenAI's API does not support true async in Python yet
                    # We're using asyncio.to_thread to avoid blocking the event loop
                    response = await asyncio.to_thread(
                        self.client.chat.completions.create,
                        model=model,
                        temperature=temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    abstract_content = response.choices[0].message.content.strip()
                    logger.info(f"Successfully abstracted plot beat {beat_index+1}/{len(plot_beats)}")
                    return {
                        "abstract_content": abstract_content,
                        "success": True
                    }
                except Exception as e:
                    logger.error(f"Error abstracting plot beat {beat_index+1}/{len(plot_beats)}: {str(e)}")
                    error_content = f"# Narrative Skeleton\n\nCould not generate abstraction due to an error: {str(e)}"
                    return {
                        "abstract_content": error_content,
                        "error": str(e),
                        "success": False
                    }
        
        # Process all beats concurrently while preserving order, but with limited concurrency
        logger.info(f"Starting concurrent processing of {len(plot_beats)} plot beats with max {MAX_CONCURRENT_TASKS} concurrent tasks")
        tasks = [process_beat(i, beat_data) for i, beat_data in enumerate(plot_beats)]
        results = await asyncio.gather(*tasks)
        
        # Check if any processing failed
        if any(not result.get("success", False) for result in results):
            self.template_repo.update_plot_beat_template_status(self.template_id, TemplateStatusEnum.FAILED)
        
        # Save results to database in the original order using batch operation
        abstract_beats = []
        if self.template_id is not None:
            repo = PlotBeatRepository(self.db)
            # Prepare batch items
            batch_items = [{
                "content": result["abstract_content"],
                "type": "TEMPLATE",
                "source_id": self.template_id
            } for result in results]
            
            try:
                repo.batch_create(batch_items)
                logger.info(f"Successfully batch created {len(batch_items)} plot beats")
            except Exception as e:
                logger.error(f"Error in batch creation of plot beats: {str(e)}")
                self.template_repo.update_plot_beat_template_status(self.template_id, TemplateStatusEnum.FAILED)
            
            # Prepare return data
            abstract_beats = [{"abstract_content": result["abstract_content"]} for result in results]
        else:
            abstract_beats = [{"abstract_content": result["abstract_content"]} for result in results]
        
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
            await self.abstract_all_character_arcs()
        
        # Step 2: Plot Beats
        if plot_beats:
            await self.abstract_plot_beats(plot_beats)
        
        logger.info("Abstraction process completed")
