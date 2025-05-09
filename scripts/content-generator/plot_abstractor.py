#!/usr/bin/env python3
import os
import sys
import json
import time
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
CHARACTER_ARC_MODEL = "gpt-4o"       # For character arc abstraction (better quality)
NARRATIVE_SKELETON_MODEL = "gpt-4o-mini"  # For plot beat abstraction (faster, cheaper)
META_STRUCTURE_MODEL = "gpt-4o"    # For overall structure abstraction (better quality)
RELATIONSHIP_MODEL = "gpt-4o"      # For relationship abstraction (better quality)

CHARACTER_ARC_TEMPERATURE = 0.3
NARRATIVE_SKELETON_TEMPERATURE = 0.3
META_STRUCTURE_TEMPERATURE = 0.3
RELATIONSHIP_TEMPERATURE = 0.3


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
        self.characters_dir = self.input_dir / "analysis/characters"
        self.plot_beats_dir = self.input_dir / "analysis/plot_beats"
        self.plot_structure_dir = self.input_dir / "analysis/plot_structure"
        self.character_growth_dir = self.input_dir / "analysis/character_growth"
        
        # Output subdirectories for templates
        self.character_arcs_dir = self.output_dir / "character_arcs"
        self.narrative_skeleton_dir = self.output_dir / "narrative_skeleton"
        self.meta_structure_dir = self.output_dir / "meta_structure"
        self.relationship_patterns_dir = self.output_dir / "relationship_patterns"
        
        # Initialize AI client
        self.client = get_openai_client()
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.character_arcs_dir.mkdir(parents=True, exist_ok=True)
        self.narrative_skeleton_dir.mkdir(parents=True, exist_ok=True)
        self.meta_structure_dir.mkdir(parents=True, exist_ok=True)
        self.relationship_patterns_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Validate input directories and load book info if database session provided"""
        # Verify input directory exists
        if not self.input_dir.exists():
            raise ValueError(f"Input directory not found: {self.input_dir}")
        
        # Verify required subdirectories exist
        required_dirs = [
            self.character_growth_dir,
            self.plot_beats_dir,
            self.plot_structure_dir
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
            return CHARACTER_ARC_MODEL, CHARACTER_ARC_TEMPERATURE
        elif abstraction_type == "narrative_skeleton":
            return NARRATIVE_SKELETON_MODEL, NARRATIVE_SKELETON_TEMPERATURE
        elif abstraction_type == "meta_structure":
            return META_STRUCTURE_MODEL, META_STRUCTURE_TEMPERATURE
        elif abstraction_type == "relationship":
            return RELATIONSHIP_MODEL, RELATIONSHIP_TEMPERATURE
        else:
            # Default to highest quality model if type not recognized
            return "gpt-4o", 0.3
    
    async def read_character_growth_files(self) -> Dict[str, str]:
        """Read all character growth files and return their contents"""
        character_files = {}
        
        # Get all markdown files except relationships.md and index files
        character_md_files = [f for f in self.character_growth_dir.glob("*.md") 
                             if f.name != "relationships.md" and f.name != "index.md"]
        
        for file_path in character_md_files:
            character_name = file_path.stem
            with open(file_path, 'r') as f:
                character_files[character_name] = f.read()
        
        return character_files
    
    async def read_relationships_file(self) -> Optional[str]:
        """Read the relationships file if it exists"""
        relationships_file = self.character_growth_dir / "relationships.md"
        
        if relationships_file.exists():
            with open(relationships_file, 'r') as f:
                return f.read()
        
        return None
    
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
    
    async def read_plot_structure_file(self) -> Optional[str]:
        """Read the overall plot structure file if it exists"""
        structure_file = self.plot_structure_dir / "overall.md"
        
        if structure_file.exists():
            with open(structure_file, 'r') as f:
                return f.read()
        
        return None
    
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
            "2. Abstract specific events into general emotional beats and developmental milestones\n"
            "3. Preserve the emotional trajectory and core lessons learned\n"
            "4. Create a structure that could be applied to any story in this genre\n"
            "5. Include psychological aspects of the character's journey\n\n"
            "Format the output as a markdown document with clear sections for:\n"
            "- Archetype Description\n"
            "- Starting State\n"
            "- Key Transformation Points (with emotional states)\n"
            "- Ending State\n"
            "- Thematic Function in Narrative\n\n"
            "IMPORTANT: Start with a title that includes the archetype. Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response. Provide the content directly in markdown format."
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
        
        character_files = await self.read_character_growth_files()
        abstract_arcs = {}
        
        for character_name, growth_content in character_files.items():
            abstract_arc = await self.abstract_character_arc(character_name, growth_content)
            abstract_arcs[character_name] = abstract_arc
            
            # Save individual arc to file
            output_file = self.character_arcs_dir / f"{character_name}_abstract.md"
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
                logger.warning(f"Error loading character mappings: {str(e)}")
        
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
                "2. Abstract specific events into general plot functions\n"
                "3. Preserve the emotional trajectory and narrative momentum\n"
                "4. Create a structure that could be applied to any story in this genre\n"
                "5. Identify the narrative function of each beat (e.g., 'introduces conflict', 'raises stakes')\n"
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
    
    async def abstract_meta_structure(self, plot_structure: str) -> Dict[str, Any]:
        """Transform the overall plot structure into a generalized meta-structure"""
        model, temperature = await self._get_model_settings("meta_structure")
        
        system_prompt = (
            "You are a narrative structure expert specializing in story architecture. "
            "Your task is to transform a specific plot structure into a generalized, "
            "reusable meta-structure by abstracting away specific details while "
            "preserving the dramatic architecture and thematic development."
        )
        
        user_prompt = (
            f"Transform the following overall plot structure into a generalized meta-structure:\n\n"
            f"{plot_structure}\n\n"
            "Follow these guidelines:\n"
            "1. Classify the structure using formal frameworks (Three-Act Structure, Hero's Journey, etc.)\n"
            "2. Replace specific story elements with universal structural components\n"
            "3. Identify key turning points and their narrative functions\n"
            "4. Abstract thematic developments into universal themes\n"
            "5. Create a blueprint that could guide the structure of any story in this genre\n\n"
            "Format the output as a markdown document with these sections:\n"
            "- Structure Classification\n"
            "- Act Breakdown\n"
            "- Key Structural Points\n"
            "- Thematic Development Pattern\n"
            "- Pacing Notes\n\n"
            "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response. Provide the content directly in markdown format."
        )
        
        logger.info("Abstracting overall meta-structure")
        logger.info(f"Using model: {model}, temperature: {temperature}")
        
        try:
            # Actual implementation with AI call
            response = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract the generated content
            meta_structure = response.choices[0].message.content.strip()
            
            # Remove any markdown code block markers if they exist
            meta_structure = meta_structure.replace('```markdown', '').replace('```', '')
            
            # Try to extract the structure type from the content
            structure_type = "Generic Structure"
            lines = meta_structure.split('\n')
            
            # Look for structure classification section
            for i, line in enumerate(lines):
                if "Structure Classification" in line and i+1 < len(lines):
                    next_line = lines[i+1].strip()
                    if next_line and not next_line.startswith('#') and not next_line.startswith('-'):
                        structure_type = next_line.split('.')[0].strip()
                        break
            
            # Save to file
            output_file = self.meta_structure_dir / "meta_structure.md"
            with open(output_file, 'w') as f:
                f.write(meta_structure)
            
            return {
                "meta_structure": meta_structure,
                "structure_type": structure_type
            }
            
        except Exception as e:
            logger.error(f"Error abstracting meta-structure: {str(e)}")
            
            # Create error message as content
            error_structure = f"# Meta-Structure Template\n\nCould not generate abstraction due to an error: {str(e)}"
            
            # Save error message to file
            output_file = self.meta_structure_dir / "meta_structure.md"
            with open(output_file, 'w') as f:
                f.write(error_structure)
            
            return {
                "meta_structure": error_structure,
                "structure_type": "Error",
                "error": str(e)
            }
    
    async def abstract_relationship_dynamics(self, relationships: str) -> Dict[str, Any]:
        """Transform specific character relationships into archetypal relationship patterns"""
        model, temperature = await self._get_model_settings("relationship")
        
        system_prompt = (
            "You are a narrative structure expert specializing in character relationships. "
            "Your task is to transform specific character relationships into generalized, "
            "reusable relationship patterns by abstracting away specific details while "
            "preserving the emotional dynamics and developmental arcs."
        )
        
        # Prepare character mapping information if available
        character_map_text = ""
        character_arcs_index = self.character_arcs_dir / "index.json"
        
        if character_arcs_index.exists():
            try:
                with open(character_arcs_index, 'r') as f:
                    character_data = json.load(f)
                
                character_mappings = {}
                for char_info in character_data.get("character_arcs", []):
                    original = char_info.get("original_character", "")
                    archetype = char_info.get("archetype", "")
                    if original and archetype:
                        # Clean up archetype if needed
                        if archetype.startswith('#'):
                            parts = archetype.split(':', 1)
                            if len(parts) > 1:
                                archetype = parts[1].strip()
                            else:
                                archetype = archetype.replace('#', '').strip()
                        
                        character_mappings[original] = archetype
                
                if character_mappings:
                    character_map_text = "\nUse these character archetype mappings when replacing character names:\n"
                    for original, archetype in character_mappings.items():
                        character_map_text += f"- {original} → {archetype}\n"
                    
                    logger.info(f"Found {len(character_mappings)} character mappings for relationship analysis")
            except Exception as e:
                logger.warning(f"Error loading character mappings for relationships: {str(e)}")
        
        user_prompt = (
            f"Transform the following character relationships into generalized relationship patterns:\n\n"
            f"{relationships}\n\n"
            "Follow these guidelines:\n"
            "1. Replace specific character names with archetypal roles\n"
            "2. Abstract the relationship dynamics into universal patterns\n"
            "3. Identify the emotional trajectory of each key relationship\n"
            "4. Create patterns that could be applied to any story in this genre\n"
            "5. Highlight the narrative function of each relationship\n"
            f"{character_map_text}\n"
            "Format each relationship pattern as:\n"
            "- [Archetype A] and [Archetype B] start as [Initial Dynamic], then evolve through [Catalyst/Event], ending in [New Relationship State]\n"
            "- Emotional trajectory: [e.g., Trust → Betrayal → Forgiveness]\n"
            "- Narrative function: [e.g., Creates subplot tension, Reinforces theme of redemption]\n\n"
            "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response. Provide the content directly in markdown format."
        )
        
        logger.info("Abstracting relationship dynamics")
        logger.info(f"Using model: {model}, temperature: {temperature}")
        
        try:
            # Actual implementation with AI call
            response = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract the generated content
            relationship_patterns = response.choices[0].message.content.strip()
            
            # Remove any markdown code block markers if they exist
            relationship_patterns = relationship_patterns.replace('```markdown', '').replace('```', '')
            
            # Save to file
            output_file = self.relationship_patterns_dir / "relationship_patterns.md"
            with open(output_file, 'w') as f:
                f.write(relationship_patterns)
            
            return {
                "relationship_patterns": relationship_patterns
            }
            
        except Exception as e:
            logger.error(f"Error abstracting relationship dynamics: {str(e)}")
            
            # Create error message as content
            error_content = f"# Relationship Pattern Template\n\nCould not generate abstraction due to an error: {str(e)}"
            
            # Save error message to file
            output_file = self.relationship_patterns_dir / "relationship_patterns.md"
            with open(output_file, 'w') as f:
                f.write(error_content)
            
            return {
                "relationship_patterns": error_content,
                "error": str(e)
            }
    
    async def extract_world_variables(self) -> Dict[str, Any]:
        """Extract world-specific variables from the abstract templates"""
        logger.info("Extracting world-specific variables from templates")
        
        # Collect all template content for analysis
        template_content = ""
        
        # Add character arc content
        character_arc_files = list(self.character_arcs_dir.glob("*_abstract.md"))
        for file_path in character_arc_files[:3]:  # Limit to first 3 to avoid token limits
            try:
                with open(file_path, 'r') as f:
                    template_content += f"\n\nCHARACTER ARC: {file_path.stem}\n{f.read()}"
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {str(e)}")
        
        # Add narrative skeleton content (first file only to avoid token limits)
        skeleton_files = list(self.narrative_skeleton_dir.glob("*_abstract.md"))
        if skeleton_files:
            try:
                with open(skeleton_files[0], 'r') as f:
                    template_content += f"\n\nNARRATIVE SKELETON:\n{f.read()}"
            except Exception as e:
                logger.warning(f"Error reading {skeleton_files[0]}: {str(e)}")
        
        # Add meta structure content
        meta_structure_file = self.meta_structure_dir / "meta_structure.md"
        if meta_structure_file.exists():
            try:
                with open(meta_structure_file, 'r') as f:
                    template_content += f"\n\nMETA-STRUCTURE:\n{f.read()}"
            except Exception as e:
                logger.warning(f"Error reading {meta_structure_file}: {str(e)}")
        
        # Add relationship patterns content
        relationships_file = self.relationship_patterns_dir / "relationship_patterns.md"
        if relationships_file.exists():
            try:
                with open(relationships_file, 'r') as f:
                    template_content += f"\n\nRELATIONSHIP PATTERNS:\n{f.read()}"
            except Exception as e:
                logger.warning(f"Error reading {relationships_file}: {str(e)}")
        
        # Use the model to extract world variables
        model, temperature = await self._get_model_settings("meta_structure")
        
        system_prompt = (
            "You are a world-building expert who can identify required story elements from abstract templates. "
            "Your task is to extract all implied or required world-specific variables that would need to be filled "
            "to generate a concrete story from abstract templates."
        )
        
        user_prompt = (
            f"From these abstract story templates, identify all implied or required world-specific variables "  
            f"that must be filled in to generate a complete story:\n\n{template_content}\n\n"
            "Group the variables into these categories:\n"
            "1. Characters: Required traits, motivations, backstories\n"
            "2. Setting: Physical locations, time periods, geographical features\n"
            "3. Society & Culture: Social structures, belief systems, traditions, laws\n"
            "4. Magic/Tech Systems: Rules, capabilities, limitations of supernatural or technological elements\n"
            "5. Events & Catalysts: Required narrative turning points or world events\n\n"
            "For each variable, provide:\n"
            "- A clear description\n"
            "- Examples of potential values\n"
            "- Any constraints or requirements\n\n"
            "Format the output as structured YAML with meaningful keys and detailed descriptions."
        )
        
        logger.info("Using AI to extract world variables")
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
            
            # Extract the generated content
            yaml_content = response.choices[0].message.content.strip()
            
            # Remove any markdown code block wrappers if present
            if yaml_content.startswith('```yaml'):
                yaml_content = yaml_content.replace('```yaml', '', 1)
            if yaml_content.endswith('```'):
                yaml_content = yaml_content.rsplit('```', 1)[0]
            
            yaml_content = yaml_content.strip()
            
            # Save to file
            world_variables_file = self.output_dir / "world_variables.yaml"
            with open(world_variables_file, 'w') as f:
                f.write(yaml_content)
                
            logger.info(f"World variables saved to {world_variables_file}")
            
            return {"world_variables": yaml_content, "file": str(world_variables_file)}
            
        except Exception as e:
            logger.error(f"Error extracting world variables: {str(e)}")
            return {"error": str(e)}
    
    async def create_template_index(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an index file for the complete template"""
        template_index = {
            "book_id": self.book_id,
            "book_title": self.book.title if self.book else f"Book {self.book_id}",
            "template_creation_date": time.strftime("%Y-%m-%d"),
            "meta_data": meta_data,
            "components": {
                "character_arcs": len(list(self.character_arcs_dir.glob("*_abstract.md"))),
                "narrative_skeleton": len(list(self.narrative_skeleton_dir.glob("*_abstract.md"))),
                "meta_structure": (self.meta_structure_dir / "meta_structure.md").exists(),
                "relationship_patterns": (self.relationship_patterns_dir / "relationship_patterns.md").exists(),
                "world_variables": (self.output_dir / "world_variables.yaml").exists()
            }
        }
        
        # Save to file
        with open(self.output_dir / "template_index.json", 'w') as f:
            json.dump(template_index, f, indent=2)
        
        return template_index
    
    async def generate_template_readme(self, template_index: Dict[str, Any]) -> None:
        """Generate a README file for the template with usage instructions"""
        # Add world variables section if available
        world_vars_text = ""
        if template_index['components'].get('world_variables', False):
            world_vars_text = """
## World Variables
The `world_variables.yaml` file contains all the specific world elements that need to be defined to create a concrete story from this template, including:
- Character-specific traits and backgrounds
- Setting details and requirements
- Cultural and societal elements
- Any magic or technology systems
- Key events and catalysts

Use this file as a "fill-in-the-blanks" guide for worldbuilding.
"""
        
        readme_content = f"""# Story Template: {template_index['book_title']}

## Overview
This template was generated based on the narrative structure of "{template_index['book_title']}" (ID: {self.book_id}).
It provides abstract patterns that can be used to create new stories with similar structural elements.

## Components
- **Character Arcs**: {template_index['components']['character_arcs']} archetypal character journeys
- **Narrative Skeleton**: {template_index['components']['narrative_skeleton']} plot beat patterns
- **Meta-Structure**: Overall story architecture and act structure
- **Relationship Patterns**: Archetypal relationship dynamics
- **World Variables**: Specific elements needed to instantiate this template{world_vars_text}

## How to Use This Template
1. Review the meta-structure to understand the overall story architecture
2. Select character archetypes that fit your story concept
3. Follow the narrative skeleton as a guide for plot progression
4. Implement relationship patterns between your characters
5. Fill in the world variables with your specific setting and character details
6. Adapt and modify as needed for your unique story

## Usage Notes
- This template provides structure, not specific content
- Add your own unique characters, settings, and situations
- The emotional journey and structural beats can be maintained while changing surface details
- Combine with other templates for more complex narratives

Created: {template_index['template_creation_date']}
"""
        
        # Save to file
        with open(self.output_dir / "README.md", 'w') as f:
            f.write(readme_content)
    
    async def run_abstraction(self) -> Dict[str, Any]:
        """Run the full abstraction pipeline"""
        logger.info(f"Starting abstraction process for book {self.book_id}")
        
        # Initialize and validate
        await self.initialize()
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Gather source data
        character_files = await self.read_character_growth_files()
        relationships = await self.read_relationships_file()
        plot_beats = await self.read_plot_beats_files()
        plot_structure = await self.read_plot_structure_file()
        
        # Check if we have the necessary data
        if not character_files:
            logger.warning("No character growth files found")
        
        if not plot_beats:
            logger.warning("No plot beats files found")
        
        if not plot_structure:
            logger.warning("No overall plot structure file found")
        
        if not relationships:
            logger.warning("No character relationships file found")
        
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
        
        # Step 3: Meta-Structure
        if plot_structure:
            # Check for existing meta-structure
            meta_structure_file = self.meta_structure_dir / "meta_structure.md"
            if meta_structure_file.exists():
                logger.info("Found existing meta-structure abstraction")
                should_continue = input("Continue with existing meta-structure? (y/n): ").strip().lower() == 'y'
                if not should_continue:
                    logger.info("Re-abstracting overall meta-structure")
                    meta_structure_data = await self.abstract_meta_structure(plot_structure)
                    meta_data["meta_structure"] = {
                        "structure_type": meta_structure_data["structure_type"]
                    }
                else:
                    logger.info("Using existing meta-structure abstraction")
                    # Just note that it exists in metadata
                    meta_data["meta_structure"] = {
                        "structure_type": "Existing Structure"
                    }
            else:
                logger.info("Abstracting overall meta-structure")
                meta_structure_data = await self.abstract_meta_structure(plot_structure)
                meta_data["meta_structure"] = {
                    "structure_type": meta_structure_data["structure_type"]
                }
        
        # Step 4: Relationship Dynamics
        if relationships:
            # Check for existing relationship patterns
            relationship_file = self.relationship_patterns_dir / "relationship_patterns.md"
            if relationship_file.exists():
                logger.info("Found existing relationship patterns abstraction")
                should_continue = input("Continue with existing relationship patterns? (y/n): ").strip().lower() == 'y'
                if not should_continue:
                    logger.info("Re-abstracting relationship dynamics")
                    relationship_data = await self.abstract_relationship_dynamics(relationships)
                    meta_data["relationship_patterns"] = {"included": True}
                else:
                    logger.info("Using existing relationship patterns abstraction")
                    meta_data["relationship_patterns"] = {"included": True}
            else:
                logger.info("Abstracting relationship dynamics")
                relationship_data = await self.abstract_relationship_dynamics(relationships)
                meta_data["relationship_patterns"] = {"included": True}
        
        # Step 5: World Variables (after all other abstractions are complete)
        has_abstractions = bool(list(self.character_arcs_dir.glob("*_abstract.md"))) or \
                         bool(list(self.narrative_skeleton_dir.glob("*_abstract.md"))) or \
                         (self.meta_structure_dir / "meta_structure.md").exists() or \
                         (self.relationship_patterns_dir / "relationship_patterns.md").exists()
        
        if has_abstractions:
            # Check for existing world variables
            world_variables_file = self.output_dir / "world_variables.yaml"
            if world_variables_file.exists():
                logger.info("Found existing world variables extraction")
                should_continue = input("Continue with existing world variables? (y/n): ").strip().lower() == 'y'
                if not should_continue:
                    logger.info("Re-extracting world-specific variables from templates")
                    world_variables_data = await self.extract_world_variables()
                    if "error" not in world_variables_data:
                        meta_data["world_variables"] = {
                            "included": True,
                            "file": world_variables_data.get("file")
                        }
                    else:
                        logger.warning("World variables extraction had errors")
                        meta_data["world_variables"] = {
                            "included": False,
                            "error": world_variables_data.get("error")
                        }
                else:
                    logger.info("Using existing world variables")
                    meta_data["world_variables"] = {
                        "included": True,
                        "file": str(world_variables_file)
                    }
            else:
                logger.info("Extracting world-specific variables from templates")
                world_variables_data = await self.extract_world_variables()
                if "error" not in world_variables_data:
                    meta_data["world_variables"] = {
                        "included": True,
                        "file": world_variables_data.get("file")
                    }
                else:
                    logger.warning("World variables extraction had errors")
                    meta_data["world_variables"] = {
                        "included": False,
                        "error": world_variables_data.get("error")
                    }
        
        # Create template index and README
        template_index = await self.create_template_index(meta_data)
        await self.generate_template_readme(template_index)
        
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