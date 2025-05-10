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
    
    async def read_character_arc_files(self) -> Dict[str, str]:
        """Read all character arc files and return their contents"""
        character_files = {}
        
        # Get index file to identify all character arc files
        index_file = self.character_arcs_input_dir / "character_arcs_index.json"
        if not index_file.exists():
            logger.warning(f"Character arcs index file not found at {index_file}")
            return {}
        
        try:
            with open(index_file, 'r') as f:
                index_data = json.load(f)
                
            # Get all markdown files for characters listed in the index
            character_names = index_data.get("characters", [])
            
            for character_name in character_names:
                # Convert character name to filename format
                filename = character_name.lower().replace(' ', '_').replace('"', '').replace("'", "") + ".md"
                file_path = self.character_arcs_input_dir / filename
                
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        character_files[character_name] = f.read()
                else:
                    logger.warning(f"Character arc file not found: {file_path}")
        except Exception as e:
            logger.error(f"Error reading character arc files: {str(e)}")
        
        return character_files
    
    # Relationship functionality has been removed
    
    async def read_plot_beats_files(self) -> List[Dict[str, Any]]:
        """Read all plot beats files and return their contents"""
        plot_beats = []
        
        # Get all markdown files except index files
        plot_beat_files = [f for f in self.plot_beats_dir.glob("*.md") 
                          if f.name != "index.md"]
        
        # Sort by chapter range
        def extract_chapter_range(filename):
            parts = filename.stem.split('_')
            if len(parts) >= 4:
                try:
                    start = int(parts[1])
                    end = int(parts[3])
                    return start
                except:
                    return 0
            return 0
        
        sorted_files = sorted(plot_beat_files, key=extract_chapter_range)
        
        for file_path in sorted_files:
            with open(file_path, 'r') as f:
                content = f.read()
                chapter_range = file_path.stem  # e.g., "chapters_1_to_10"
                
                plot_beats.append({
                    "range": chapter_range,
                    "content": content
                })
        
        return plot_beats
    
    # Plot structure functionality has been removed
    
    async def abstract_character_arc(self, character_name: str, character_growth: str) -> Dict[str, Any]:
        """Transform a specific character's growth into a generalized arc structure"""
        model, temperature = await self._get_model_settings("character_arc")
        
        system_prompt = (
            "You are a narrative structure expert specializing in character arc abstraction. "
            "Your task is to transform a specific character's growth arc into a generalized, "
            "reusable template by abstracting away specific details while preserving the "
            "emotional and developmental journey."
        )
        
        user_prompt = (
            f"Transform the following character growth analysis into a generalized character arc template:\n\n"
            f"{character_growth}\n\n"
            "Follow these guidelines:\n"
            "1. Replace the specific character name with a general archetype (e.g., 'The Mentor', 'The Rebel')\n"
            "2. Preserve the nature of the relationship between the characters\n"
            "3. Preserve the emotional trajectory and core lessons learned\n"
            "4. Create a structure that could be applied to any story in the romance genre\n"
            "5. Preserve the Personality and the relationship dynamic between the characters\n"
            "Format the output as the source text\n"
            "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response. Provide the content directly in markdown format."
        )
        
        logger.info(f"Abstracting character arc for: {character_name}")
        logger.info(f"Using model: {model}, temperature: {temperature}")
        
        # Actual implementation with AI call
        try:
            response = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract the generated content
            abstract_content = response.choices[0].message.content.strip()
            
            # Remove any markdown code block markers if they exist
            abstract_content = abstract_content.replace('```markdown', '').replace('```', '')
            
            # Use the first line as the archetype title without complex parsing
            lines = abstract_content.split('\n')
            archetype = lines[0] if lines else "Unknown Archetype"
                
            return {
                "original_character": character_name,
                "archetype": archetype,
                "abstract_arc": abstract_content,
            }
            
        except Exception as e:
            logger.error(f"Error abstracting character arc: {str(e)}")
            # Return a placeholder on error
            return {
                "original_character": character_name,
                "archetype": f"The [Derived Archetype for {character_name}]",
                "abstract_arc": f"# Character Arc Template\n\nCould not generate abstraction due to an error: {str(e)}",
            }
    
    async def abstract_all_character_arcs(self) -> Dict[str, Any]:
        """Abstract all character arcs into generalized templates"""
        logger.info("Abstracting all character arcs")
        
        character_files = await self.read_character_arc_files()
        abstract_arcs = {}
        
        for character_name, arc_content in character_files.items():
            abstract_arc = await self.abstract_character_arc(character_name, arc_content)
            abstract_arcs[character_name] = abstract_arc
            
            # Save individual arc to file
            # Convert character name to a filename-safe format
            safe_name = character_name.lower().replace(' ', '_').replace('"', '').replace("'", "")
            output_file = self.character_arcs_dir / f"{safe_name}_abstract.md"
            with open(output_file, 'w') as f:
                f.write(abstract_arc["abstract_arc"])
        
        # Create index of all abstractions
        index_data = {
            "character_arcs": [
                {
                    "original_character": character_name,
                    "archetype": arc_data["archetype"],
                    "file": f"{character_name}_abstract.md"
                }
                for character_name, arc_data in abstract_arcs.items()
            ]
        }
        
        with open(self.character_arcs_dir / "index.json", 'w') as f:
            json.dump(index_data, f, indent=2)
        
        return abstract_arcs
    
    async def abstract_plot_beats(self, plot_beats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform specific plot beats into a generalized narrative skeleton"""
        model, temperature = await self._get_model_settings("narrative_skeleton")
        
        # Get character mappings from the already abstracted character arcs
        character_mappings = {}
        character_arcs_index = self.character_arcs_dir / "index.json"
        
        if character_arcs_index.exists():
            try:
                with open(character_arcs_index, 'r') as f:
                    character_data = json.load(f)
                    
                for char_info in character_data.get("character_arcs", []):
                    original = char_info.get("original_character", "")
                    archetype = char_info.get("archetype", "")
                    if original and archetype:
                        # Clean up archetype if needed (remove markdown headers etc.)
                        if archetype.startswith('#'):
                            parts = archetype.split(':', 1)
                            if len(parts) > 1:
                                archetype = parts[1].strip()
                            else:
                                archetype = archetype.replace('#', '').strip()
                                
                        character_mappings[original] = archetype
                        
                logger.info(f"Found {len(character_mappings)} character mappings")
            except Exception as e:
                logger.warning(f"Error loading character mappings from abstract index: {str(e)}")
        
        # If no character mappings from abstractions, try to get role information directly from character arc files
        if not character_mappings:
            try:
                character_files = await self.read_character_arc_files()
                for character_name, content in character_files.items():
                    # Extract the Role section from each character's markdown file
                    role_match = re.search(r"## Role\s*([^#]*?)(?=\s*##|\s*$)", content, re.DOTALL)
                    if role_match:
                        role = role_match.group(1).strip()
                        character_mappings[character_name] = f"The {role}" if not role.startswith("The ") else role
                        
                logger.info(f"Extracted {len(character_mappings)} character roles directly from character arcs")
            except Exception as e:
                logger.warning(f"Error extracting character roles: {str(e)}")
        
        abstract_beats = []
        
        for beat_data in plot_beats:
            chapter_range = beat_data["range"]
            content = beat_data["content"]
            
            system_prompt = (
                "You are a narrative structure expert specializing in plot abstraction. "
                "Your task is to transform specific plot beats into a generalized, "
                "reusable narrative skeleton by abstracting away specific details while "
                "preserving the dramatic structure and emotional impact."
            )
            
            # Prepare character mapping information if available
            character_map_text = ""
            if character_mappings:
                character_map_text = "\nUse these character archetype mappings when replacing character names:\n"
                for original, archetype in character_mappings.items():
                    character_map_text += f"- {original} → {archetype}\n"
            
            user_prompt = (
                f"Transform the following plot beats into a generalized narrative skeleton:\n\n"
                f"{content}\n\n"
                "Follow these guidelines:\n"
                "1. Replace specific character names with general roles or archetypes\n"
                "2. Preserve the emotional trajectory and narrative momentum\n"
                "3. Preserve the main genre as Romance, sub genre and trope. Ex: Billionare Romance, Mafia Romance, Contract Marriage, Slow burn Romanceetc.\n"
                "4. Identify the narrative function of each beat (e.g., 'introduces conflict', 'raises stakes')\n"
                f"{character_map_text}\n"
                "Format the output as a markdown document with numbered beats and their narrative functions.\n\n"
                "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response."
            )
            
            logger.info(f"Abstracting plot beats for range: {chapter_range}")
            logger.info(f"Using model: {model}, temperature: {temperature}")
            
            # Actual implementation with AI call
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                # Extract the generated content
                abstract_content = response.choices[0].message.content.strip()
                
                abstract_beats.append({
                    "range": chapter_range,
                    "abstract_content": abstract_content
                })
                
                # Save to file
                output_file = self.narrative_skeleton_dir / f"{chapter_range}_abstract.md"
                with open(output_file, 'w') as f:
                    f.write(abstract_content)
                    
            except Exception as e:
                logger.error(f"Error abstracting plot beats for {chapter_range}: {str(e)}")
                
                # Create an error message as the content
                error_content = f"# Narrative Skeleton: {chapter_range}\n\nCould not generate abstraction due to an error: {str(e)}"
                
                abstract_beats.append({
                    "range": chapter_range,
                    "abstract_content": error_content,
                    "error": str(e)
                })
                
                # Save error message to file
                output_file = self.narrative_skeleton_dir / f"{chapter_range}_abstract.md"
                with open(output_file, 'w') as f:
                    f.write(error_content)
        
        return abstract_beats
    
    async def create_template_index(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an index file for the complete template"""
        template_index = {
            "book_id": self.book_id,
            "book_title": self.book.title if self.book else f"Book {self.book_id}",
            "template_creation_date": time.strftime("%Y-%m-%d"),
            "meta_data": meta_data,
            "components": {
                "character_arcs": len(list(self.character_arcs_dir.glob("*_abstract.md"))),
                "narrative_skeleton": len(list(self.narrative_skeleton_dir.glob("*_abstract.md")))
            }
        }
        
        # Save to file
        with open(self.output_dir / "template_index.json", 'w') as f:
            json.dump(template_index, f, indent=2)
        
        return template_index
    
    async def run_abstraction(self) -> Dict[str, Any]:
        """Run the full abstraction pipeline"""
        logger.info(f"Starting abstraction process for book {self.book_id}")
        
        # Initialize and validate
        await self.initialize()
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Gather source data
        character_files = await self.read_character_arc_files()
        plot_beats = await self.read_plot_beats_files()
        
        # Check if we have the necessary data
        if not character_files:
            logger.warning("No character arc files found")
        
        if not plot_beats:
            logger.warning("No plot beats files found")
        
        # Run abstractions
        meta_data = {}
        
        # Step 1: Character Arcs
        if character_files:
            # Check for existing character arcs
            existing_arcs = list(self.character_arcs_dir.glob("*_abstract.md"))
            if existing_arcs:
                logger.info(f"Found {len(existing_arcs)} existing character arc abstractions")
                should_continue = input("Continue with existing character arcs? (y/n): ").strip().lower() == 'y'
                if not should_continue:
                    logger.info(f"Re-abstracting {len(character_files)} character arcs")
                    abstract_arcs = await self.abstract_all_character_arcs()
                    meta_data["character_arcs"] = {
                        "count": len(abstract_arcs),
                        "archetypes": [arc_data["archetype"] for character, arc_data in abstract_arcs.items()]
                    }
                else:
                    logger.info("Using existing character arc abstractions")
                    # Still capture metadata from existing files
                    character_index_path = self.character_arcs_dir / "index.json"
                    if character_index_path.exists():
                        with open(character_index_path, 'r') as f:
                            char_index = json.load(f)
                            meta_data["character_arcs"] = {
                                "count": len(char_index.get("character_arcs", [])),
                                "archetypes": [arc.get("archetype") for arc in char_index.get("character_arcs", [])]
                            }
            else:
                logger.info(f"Abstracting {len(character_files)} character arcs")
                abstract_arcs = await self.abstract_all_character_arcs()
                meta_data["character_arcs"] = {
                    "count": len(abstract_arcs),
                    "archetypes": [arc_data["archetype"] for character, arc_data in abstract_arcs.items()]
                }
        
        # Step 2: Plot Beats
        if plot_beats:
            # Check for existing narrative skeleton
            existing_beats = list(self.narrative_skeleton_dir.glob("*_abstract.md"))
            if existing_beats:
                logger.info(f"Found {len(existing_beats)} existing narrative skeleton abstractions")
                should_continue = input("Continue with existing narrative skeleton? (y/n): ").strip().lower() == 'y'
                if not should_continue:
                    logger.info(f"Re-abstracting {len(plot_beats)} plot beat sections")
                    abstract_beats = await self.abstract_plot_beats(plot_beats)
                    meta_data["narrative_skeleton"] = {
                        "sections": len(abstract_beats),
                        "ranges": [beat["range"] for beat in abstract_beats]
                    }
                else:
                    logger.info("Using existing narrative skeleton abstractions")
                    # Capture metadata from existing files
                    meta_data["narrative_skeleton"] = {
                        "sections": len(existing_beats),
                        "ranges": [path.stem.replace("_abstract", "") for path in existing_beats]
                    }
            else:
                logger.info(f"Abstracting {len(plot_beats)} plot beat sections")
                abstract_beats = await self.abstract_plot_beats(plot_beats)
                meta_data["narrative_skeleton"] = {
                    "sections": len(abstract_beats),
                    "ranges": [beat["range"] for beat in abstract_beats]
                }
        
        template_index = await self.create_template_index(meta_data)
        
        logger.info("Abstraction process completed")
        
        return template_index


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