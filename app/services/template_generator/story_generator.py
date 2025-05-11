#!/usr/bin/env python3
import os
import sys
import json
import re
import time
import asyncio
import traceback
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Add the project root to the Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import from app services
from app.services.ai_service import get_openai_client

# Import prompt templates
from prompts.story_generator_prompts import (
    CHARACTER_ARC_SYSTEM_PROMPT,
    CHARACTER_ARC_USER_PROMPT_TEMPLATE,
    PLOT_BEAT_SYSTEM_PROMPT,
    PLOT_BEAT_USER_PROMPT_TEMPLATE
)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / 'story_generator.log')
    ]
)
logger = logging.getLogger('story_generator')

# Utility functions for user input
def get_yes_no_input(prompt, default=None):
    """
    Get a yes/no response from the user.
    
    Args:
        prompt (str): The prompt to display to the user
        default (bool): Default value if user just presses Enter
        
    Returns:
        bool: True for yes, False for no
    """
    if default is True:
        display_prompt = f"{prompt}? (Y/n): "
        default_response = 'y'
    elif default is False:
        display_prompt = f"{prompt}? (y/N): "
        default_response = 'n'
    else:
        display_prompt = f"{prompt}? (y/n): "
        default_response = None
        
    while True:
        response = input(display_prompt).strip().lower()
        
        if not response and default_response:
            response = default_response
            
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'.")

def get_validated_input(prompt, required=False, input_type=None, options=None):
    """Get user input with validation.
    
    Args:
        prompt (str): The prompt to display to the user
        required (bool): Whether the input is required
        input_type (str): Type of input to validate ('list', 'int', etc.)
        options (list): List of valid options if applicable
        
    Returns:
        The validated input
    """
    while True:
        if required:
            display_prompt = f"{prompt} (required): "
        else:
            display_prompt = prompt
            
        value = input(display_prompt).strip()
        
        # Check if required
        if required and not value:
            print(f"This field is required. Please enter a value.")
            continue
            
        # If not required and empty, return empty
        if not required and not value:
            return value
            
        # Validate type if specified
        if input_type == 'list' and value:
            # Convert comma-separated string to list
            result = [item.strip() for item in value.split(',') if item.strip()]
            if required and not result:
                print(f"Please enter at least one value.")
                continue
            return result
        elif input_type == 'int' and value:
            try:
                return int(value)
            except ValueError:
                print(f"Please enter a valid number.")
                continue
                
        # Validate against options if specified
        if options and value not in options:
            print(f"Please enter one of: {', '.join(options)}")
            continue
            
        return value

# Constants
TEMPLATE_BASE_DIR = Path(__file__).parent / "output"

# Hardcoded AI model settings for story generation
CHARACTER_MODEL = "gpt-4o"   # For character arc generation
PLOT_MODEL = "gpt-4o"        # For plot beat generation
SUMMARY_MODEL = "gpt-4o"     # For plot summary generation

# Temperature settings
CHARACTER_TEMPERATURE = 0.7  # Higher temperature for creative character generation
PLOT_TEMPERATURE = 0.7       # Higher temperature for creative plot generation
SUMMARY_TEMPERATURE = 0.4    # Lower temperature for more concise and accurate summaries


class StoryGenerator:
    def __init__(self, book_id: int):
        """Initialize the story generator with a book ID"""
        self.book_id = book_id
        
        # Set up directories
        self.template_dir = TEMPLATE_BASE_DIR
        
        # Set up book-specific directories for templates
        self.book_template_dir = TEMPLATE_BASE_DIR / f"book_{book_id}/template"
        
        # Create parallel directories for generated content
        self.book_base_dir = TEMPLATE_BASE_DIR / f"book_{book_id}"
        self.generated_arcs_dir = self.book_base_dir / "generated_arcs"
        self.character_arcs_dir = self.generated_arcs_dir / "character_arcs"
        self.plot_beats_dir = self.generated_arcs_dir / "plot_beats"
        
        # Create the directories if they don't exist
        self.generated_arcs_dir.mkdir(parents=True, exist_ok=True)
        self.character_arcs_dir.mkdir(parents=True, exist_ok=True)
        self.plot_beats_dir.mkdir(parents=True, exist_ok=True)
            
        # Initialize AI client
        try:
            self.client = get_openai_client()
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI client: {str(e)}")
            self.client = None
            
        # Make sure output directories exist
        if not self.book_id:
            # Only need to create output_dir for standalone mode
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
        # Store for character arc and plot beat templates
        self.character_arc_templates = []  # Will store {"name": name, "content": content}
        self.plot_beat_templates = []      # Will store {"name": name, "content": content}
        
        # Store for generated character arcs and plot beats
        self.generated_character_arcs = []  # Will store loaded character arcs
        
    async def initialize(self):
        """Initialize templates and directories"""
        # Verify book template directory exists
        if not self.book_template_dir or not self.book_template_dir.exists():
            logger.warning(f"Template directory for book {self.book_id} not found at {self.book_template_dir}")
            return False
        
        # Load character arc templates
        await self._load_character_arc_templates()
        
        # Load plot beat templates
        await self._load_plot_beat_templates()
            
        logger.info(f"Initialized Story Generator for book ID: {self.book_id} with {len(self.character_arc_templates)} character templates and {len(self.plot_beat_templates)} plot beat templates")
        return True
    
    async def _get_model_settings(self, generation_type: str):
        """Get AI model settings based on generation type"""
        # Use hardcoded settings based on generation type
        if generation_type == "character":
            return CHARACTER_MODEL, CHARACTER_TEMPERATURE
        elif generation_type == "plot":
            return PLOT_MODEL, PLOT_TEMPERATURE
        elif generation_type == "summary":
            return SUMMARY_MODEL, SUMMARY_TEMPERATURE
        else:
            # Default to highest quality model if type not recognized
            return "gpt-4o", 0.5
    
    async def _load_character_arc_templates(self) -> List[Dict[str, str]]:
        """Load character arc templates with their content and populate class variable (internal method)
        
        Returns:
            List[Dict[str, str]]: A list of dictionaries with template name and content
        """
        # Clear existing templates
        self.character_arc_templates = []
        
        # Direct path to character arc templates
        character_arcs_dir = self.book_template_dir / "character_arcs"
        
        # Check if directory exists
        if not character_arcs_dir.exists():
            logger.warning(f"Character arcs directory not found at {character_arcs_dir}")
            return self.character_arc_templates
        
        # Look for all markdown files ending with _abstract.md
        character_files = list(character_arcs_dir.glob("*_abstract.md"))
        
        # Load content of each file
        for file_path in character_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                self.character_arc_templates.append({
                    "name": file_path.name,
                    "content": content
                })
                
            except Exception as e:
                logger.error(f"Error loading character template {file_path.name}: {str(e)}")
        
        logger.info(f"Loaded {len(self.character_arc_templates)} character arc templates with content")
        return self.character_arc_templates
    

    
    async def _load_plot_beat_templates(self) -> List[Dict[str, str]]:
        """Load plot beat templates with their content and populate class variable (internal method)
        
        Returns:
            List[Dict[str, str]]: A list of dictionaries with template name and content
        """
        # Clear existing templates
        self.plot_beat_templates = []
        
        # Direct path to plot beat templates
        narrative_dir = self.book_template_dir / "narrative_skeleton"
        
        # Check if directory exists
        if not narrative_dir.exists():
            logger.warning(f"Narrative skeleton directory not found at {narrative_dir}")
            return self.plot_beat_templates
        
        # Look for all markdown files
        plot_files = list(narrative_dir.glob("*.md"))
        
        # Load content of each file
        for file_path in plot_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                self.plot_beat_templates.append({
                    "name": file_path.name.replace('.md', ''),
                    "content": content
                })

                #sort templates by name
                self.plot_beat_templates.sort(key=lambda x: x['name'])
            except Exception as e:
                logger.error(f"Error loading plot template {file_path.name}: {str(e)}")
        
        logger.info(f"Loaded {len(self.plot_beat_templates)} plot beat templates with content")
        return self.plot_beat_templates
        

    
    async def generate_characters_from_prompt(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Generate multiple character arcs from a single prompt
        
        This method takes a simple prompt and automatically creates multiple interconnected
        character arcs based on all available character templates.
        
        Args:
            prompt: A brief description of the story or character ensemble needed

        Returns:
            A list of generated character arcs
        """
        
        # Process templates into the format needed for generation
        loaded_templates = await self._process_character_templates(self.character_arc_templates)
        
        if not loaded_templates:
            error_msg = "Could not process any valid character templates"
            logger.error(error_msg)
            return [{"error": error_msg}]
            
        model, temperature = await self._get_model_settings("character")
        
        # Use the imported system prompt for character arc generation
        system_prompt = CHARACTER_ARC_SYSTEM_PROMPT
        
        # Create descriptions of available templates
        template_descriptions = []
        for i, template in enumerate(loaded_templates, 1):
            template_descriptions.append(f"### Template {i}: {template.get('content', 'No content available')}")
        
        # Format the user prompt template with the template descriptions and prompt
        template_descriptions_text = "\n\n".join(template_descriptions)
        user_prompt = CHARACTER_ARC_USER_PROMPT_TEMPLATE.format(
            prompt=prompt,
            template_descriptions=template_descriptions_text
        )
        
        try:
            logger.info(f"Generating character arcs from prompt...")
            
            response = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            character_markdown_content = response.choices[0].message.content
            
            # Save the complete character arc output
            complete_analysis_path = self.character_arcs_dir / "complete_character_arcs.md"
            with open(complete_analysis_path, 'w', encoding='utf-8') as f:
                f.write(character_markdown_content)
                
            logger.info(f"Complete character analysis saved to {complete_analysis_path}")
            
            # Extract individual character files using regex pattern
            pattern = r"CHARACTER:\s*([^\n]+)\s*\nFILE_START\s*\n([\s\S]*?)\nFILE_END"
            matches = re.findall(pattern, character_markdown_content)
            
            logger.info(f"Found {len(matches)} character matches in the generated content")
            
            # Use the character arcs directory
            output_dir = self.character_arcs_dir
            
            # Process each character section
            results = []
            character_names = []
            for name, content in matches:
                character_name = name.strip()
                character_names.append(character_name)
                character_content = content.strip()
                
                # Remove markdown code block delimiters if present
                character_content = re.sub(r'^```markdown\n', '', character_content)
                character_content = re.sub(r'\n```$', '', character_content)
                character_content = re.sub(r'^```\n', '', character_content)
                character_content = character_content.strip()
                
                # Create a safe filename
                character_filename = character_name.lower().replace(' ', '_').replace('"', '').replace("'", "") + ".md"
                file_path = output_dir / character_filename
                
                # Just save the character arc file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(character_content)
                    
                logger.info(f"Character arc for {character_name} saved to {file_path}")
                
                # Add minimal info to results
                results.append({
                    "name": character_name,
                    "content": character_content,
                    "file_path": str(file_path)
                })
            
            # Skip creating JSON index file - directly use the file structure
            
            return results
            
        except Exception as e:
            error_message = f"Error generating character arcs: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return [{"error": error_message}]
            
    async def _process_character_templates(self, template_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw character templates into the format needed for generation
        
        Args:
            template_list: List of raw templates with name and content
            
        Returns:
            List of processed templates with template_id, archetype, character_name, and content
        """
        processed_templates = []
        
        for template_info in template_list:
            try:
                # Extract template data from the input
                file_name = template_info.get('name', '')
                content = template_info.get('content', '')
                
                # Extract character name from filename
                character_name = file_name.replace("_abstract.md", "").replace("_", " ").title()
                
                # Extract archetype from file content
                archetype = f"Character Template for {character_name}"
                first_line = content.split('\n')[0].strip()
                if first_line.startswith('#'):
                    archetype = first_line.lstrip('#').strip()
                
                # Create template object
                template = {
                    "template_id": f"char_{self.book_id}_{character_name.lower().replace(' ', '_')}",
                    "archetype": archetype,
                    "character_name": character_name,
                    "content": content
                }
                
                processed_templates.append(template)
                logger.debug(f"Processed character template: {archetype}")
                
            except Exception as e:
                logger.warning(f"Error processing template {file_name}: {str(e)}")
                continue
                
        return processed_templates
        
    # All individual character generation methods have been removed in favor of the prompt-based approach
    
    async def generate_plot_beats_from_prompt(self, template_id: str, prompt: str, character_arcs: List[Dict[str, Any]], plot_till_now: str) -> Dict[str, Any]:
        """
        Generate plot beats from a simple prompt and the generated character arcs
        
        This method takes a simple prompt and automatically creates plot beats that
        incorporate all the character arcs in a cohesive narrative.
        
        Args:
            template_id: The ID of the plot template to use
            prompt: A brief description of the desired plot
            character_arcs: List of previously generated character arcs
            plot_till_now: String containing the plot summarized so far
            
        Returns:
            A dictionary containing the generated plot beats
        """
        # Check if plot beat templates are loaded
        if not self.plot_beat_templates:
            # Load templates if not already loaded
            await self._load_plot_beat_templates()
            
        if not self.plot_beat_templates:
            error_msg = "No plot beat templates available"
            logger.error(error_msg)
            return {"error": error_msg}
            
        # Find the requested template by template_id
        template = None
        for plot_template in self.plot_beat_templates:
            # Create a template ID from the filename
            file_name = plot_template.get('name', '')
            current_id = file_name.replace('.md', '').lower()
            
            if current_id == template_id.lower():
                template = plot_template
                break
                
        if not template:
            error_msg = f"Plot beat template with ID '{template_id}' not found"
            logger.error(error_msg)
            return {"error": error_msg}
        
        model, temperature = await self._get_model_settings("plot")
        
        # Use the imported system prompt for plot beat generation
        system_prompt = PLOT_BEAT_SYSTEM_PROMPT
        
        # Prepare character content by combining character arcs
        character_content = ""
        for arc in character_arcs:
            character_content += f"### {arc.get('name', 'Unknown Character')}\n"
            character_content += f"{arc.get('content', 'No character information')}\n\n"
            
        # Format the user prompt template with the necessary variables
        user_prompt = PLOT_BEAT_USER_PROMPT_TEMPLATE.format(
            template_content=template.get('content', 'No template content'),
            prompt=prompt,
            character_content=character_content,
            plot_till_now=plot_till_now
        )
        
        try:
            # Use the template_id directly as the name
            title = template_id
                
            logger.info(f"Generating plot beats using template {template_id}")
            logger.info(f"Using model: {model}, temperature: {temperature}")
            
            response = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            plot_content = response.choices[0].message.content.strip()
            
            # Create a filename based on the template_id
            safe_title = template_id.replace('/', '_').replace('\\', '_')
            safe_title = re.sub(r'[^a-z0-9_-]', '', safe_title)
            
            # Use the plot beats directory
            output_dir = self.plot_beats_dir
            output_file = output_dir / f"{safe_title}.md"
                
            with open(output_file, 'w') as f:
                f.write(plot_content)
                
            logger.info(f"Plot beats saved to {output_file}")
            
            # Return the generated plot with metadata
            return plot_content
            
        except Exception as e:
            error_message = f"Error generating plot beats: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return {"error": error_message}
    
    async def summarize_plot_till_now(self, plot_beats_till_now: str) -> str:
        """
        Generate a concise summary of the plot beats generated so far
        
        This method takes the accumulated plot beats and creates a summary to use
        as context for generating subsequent plot beats.
        
        Args:
            plot_beats_till_now: String containing all plot beats generated so far
            
        Returns:
            A concise summary of the plot progression
        """
        try:
            # Get model settings for summary generation
            model, temperature = await self._get_model_settings("summary")
            
            system_prompt = (
                "You are a literary expert specializing in narrative structure and plot analysis. "
                "Your task is to create a concise, coherent summary of plot beats that have been generated so far. "
                "The summary should capture the key developments, character arcs, and narrative progression "
                "in a way that provides clear context for generating the next plot beats."
                "end of the story focus on the final plot beats"
            )
            
            user_prompt = f"""
            # Plot Summary Task
            
            ## Plot Beats Generated So Far:
            ```
            {plot_beats_till_now}
            ```
            
            ## Instructions:
            Provide a concise summary (300-500 words) of the plot so far, focusing on:
            1. The main narrative threads and how they've developed
            2. Key character developments and transformations
            3. Important plot points and their significance
            4. The current state of the story (where things stand now)
            
            Your summary should maintain narrative continuity and highlight elements that will be important
            for generating subsequent plot beats. Avoid unnecessary details while preserving the essential
            structure and progression of the story.
            """
            
            logger.info(f"Generating plot summary using model: {model}, temperature: {temperature}")
            
            response = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            summary_content = response.choices[0].message.content.strip()
            
            # Save the summary to a file for reference
            output_dir = self.book_base_dir / "summaries"
            output_dir.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            output_file = output_dir / f"plot_summary_{timestamp}.md"
            
            with open(output_file, 'w') as f:
                f.write(summary_content)
                
            logger.info(f"Plot summary saved to {output_file}")
            
            return summary_content
            
        except Exception as e:
            error_message = f"Error generating plot summary: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            # Return an empty string on error, so the generation can continue without the summary
            return ""