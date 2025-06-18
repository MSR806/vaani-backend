#!/usr/bin/env python3
import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

from app.models.models import CharacterArc as CharacterArcModel
from app.schemas.character_arcs import CharacterArc, CharacterArcContentJSON
from app.models.models import CharacterArc as CharacterArcModel
from app.prompts.story_generator_prompts import CHARACTER_ARC_SYSTEM_PROMPT, CHARACTER_ARC_USER_PROMPT_TEMPLATE, CHARACTER_ARC_EVOLUTION_USER_PROMPT_TEMPLATE

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Maximum number of concurrent tasks for API calls
MAX_CONCURRENT_TASKS = 5

def get_character_arcs_content_by_chapter_id(character_arcs: List[CharacterArcModel], chapter_id: int, mentioned_archetypes: set = None) -> List[Tuple[str, str, int]]:
    character_arcs_content = []
    for character_arc in character_arcs:
        # Skip characters not mentioned in the plot template if mentioned_archetypes is provided
        if mentioned_archetypes is not None and character_arc.archetype not in mentioned_archetypes:
            continue
            
        #chapter range = [start, end]
        character_arc_json = CharacterArcContentJSON(**character_arc.content_json)
        for chapter_range_content in character_arc_json.chapter_range_content:
            if chapter_id >= chapter_range_content.chapter_range[0] and chapter_id <= chapter_range_content.chapter_range[1]:
                character_arcs_content.append((character_arc.name, chapter_range_content.content, character_arc.id))
    return character_arcs_content

async def generate_character_arc_content(
    template_content: str,
    story_prompt: str,
    character_mappings: str,
    client,
    model: str,
    temperature: float,
    previous_arc: Optional[str] = None,
    chapter_range: str = ""  # Added to track the chapter range info
) -> Dict[str, Any]:
    
    try:
        # Determine if this is the first range or a subsequent one
        is_first_range = previous_arc is None
        character_name = "Character"  # Default name used for logging
        
        # Extract potential character name from template content for better logs
        name_match = re.search(r'# ([^-]+)', template_content)
        if name_match:
            character_name = name_match.group(1).strip()
        
        # Choose the appropriate prompt template based on whether it's the first range
        if is_first_range:
            # Use the initial prompt template for the first range
            user_prompt = CHARACTER_ARC_USER_PROMPT_TEMPLATE.format(
                prompt=story_prompt,
                character_arc_template=template_content,
                character_mappings=character_mappings
            )
        else:
            # Use the evolution prompt template for subsequent ranges
            user_prompt = CHARACTER_ARC_EVOLUTION_USER_PROMPT_TEMPLATE.format(
                prompt=story_prompt,
                previous_character_arc=previous_arc,
                character_arc_template=template_content,
                character_mappings=character_mappings
            )
        
        # Run the OpenAI API call in a separate thread to avoid blocking the event loop
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=[
                {"role": "system", "content": CHARACTER_ARC_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature
        )
        
        generated_content = response.choices[0].message.content.strip()
        
        # Log success
        logger.info(f"Successfully generated character arc content for {character_name} - {chapter_range}")
        
        return {
            "chapter_range": chapter_range,
            "content": generated_content,
            "success": True
        }
    except Exception as e:
        error_msg = f"Error generating character arc for {character_name} - {chapter_range}: {str(e)}"
        logger.error(error_msg)
        return {
            "chapter_range": chapter_range,
            "content": f"# Character Arc Error\n\nCould not generate content due to an error: {str(e)}",
            "success": False,
            "error": str(e)
        }


async def generate_character_arc(template: CharacterArcModel, character_mappings: str, story_prompt: str, client, model: str, temperature: float):
    logger.info(f"Generating character arc for {template.archetype}")
    character_arc_json = CharacterArcContentJSON(**template.content_json)
    name = template.archetype
    
    # Process chapter ranges sequentially to maintain character consistency
    results = []
    previous_arc = None
    
    # Sort chapter ranges by their starting chapter number
    # Access chapter_range property of each content item for sorting
    sorted_chapter_ranges = sorted(character_arc_json.chapter_range_content, 
                                 key=lambda x: x.chapter_range[0])
    
    # Process each chapter range in sequence
    for idx, template_content in enumerate(sorted_chapter_ranges):
        logger.info(f"Starting segment {idx+1}/{len(character_arc_json.chapter_range_content)} for character {name}")
        
        # Extract chapter range for better tracking
        chapter_range = template_content.chapter_range
        
        # Generate character arc content for this range, passing previous_arc for consistency
        result = await generate_character_arc_content(
            template_content=template_content.content,
            story_prompt=story_prompt,
            character_mappings=character_mappings,
            client=client,
            model=model,
            temperature=temperature,
            previous_arc=previous_arc,
            chapter_range=chapter_range
        )
        
        results.append(result)
        
        # Store this result's content as the previous_arc for the next iteration
        if result.get("success", False):
            previous_arc = result.get("content", None)
        
        logger.info(f"Completed segment {idx+1}/{len(character_arc_json.chapter_range_content)} for character {name}")
    
    logger.info(f"Completed sequential generation of {len(results)} chapter segments for character {name}")
    
    return results


async def process_character_arcs(
    character_templates: List[CharacterArcModel],
    character_mappings: str,
    story_prompt: str,
    client,
    model: str,
    temperature: float
) -> List[CharacterArc]:
    """
    Process character arcs for multiple characters in parallel. 
    For each character, chapter ranges are processed sequentially to maintain consistency.
    """
    logger.info(f"Processing {len(character_templates)} character arcs")
    generation_tasks = {}
    results = []

    for template in character_templates:
        name = template.archetype
        
        # Create a task for sequential generation of this character's arc across chapter ranges
        task = generate_character_arc(
            template=template,
            character_mappings=character_mappings,
            story_prompt=story_prompt,
            client=client,
            model=model,
            temperature=temperature
        )
        
        generation_tasks[name] = task
    
    if generation_tasks:
        # Get the names in a fixed order to match with results
        names = list(generation_tasks.keys())
        tasks = list(generation_tasks.values())
        
        # Execute all character tasks concurrently
        # (each character's chapter ranges are still processed sequentially inside generate_character_arc)
        all_character_results = await asyncio.gather(*tasks)
        
        # Process results for each character
        for i, name in enumerate(names):
            # Find the corresponding template
            template = next((t for t in character_templates if t.archetype == name), None)
            if not template:
                logger.warning(f"Could not find template for character {name}")
                continue
                
            # Get the results for this character (list of chapter range results)
            character_results = all_character_results[i]
            
            # Populate chapter_range_content for the character
            chapter_range_content = []
            for result in character_results:
                if result.get("success", False):
                    chapter_range_content.append({
                        "chapter_range": result.get("chapter_range", ""),
                        "content": result.get("content", "")
                    })
            
            # Extract name, role, and other details from the first content segment if available
            character_name = template.name
            character_role = template.role
            
            # Extract information from the first chapter range content
            if chapter_range_content and "content" in chapter_range_content[0]:
                first_content = chapter_range_content[0]["content"]
                lines = first_content.split("\n")
                
                # Extract name from header (format: "# Character Name")
                for line in lines:
                    if line.startswith("# "):
                        character_name = line[2:].strip()
                        # Remove any " - Role" suffix if present
                        if " - " in character_name:
                            character_name = character_name.split(" - ", 1)[0].strip()
                        break
                
                # Extract role from the "## Role" section
                role_pattern = r"## Role\s*\n([^#]*?)(?:\n##|$)"
                role_match = re.search(role_pattern, first_content)
                if role_match:
                    character_role = role_match.group(1).strip()
            
            # Create the CharacterArc object
            character_arc = CharacterArc(
                name=character_name,
                archetype=template.archetype,  # This contains char_1, char_2, etc.
                role=character_role,
                type=template.type,
                content_json={
                    "chapter_range_content": chapter_range_content,
                    "blood_relations": template.content_json.get("blood_relations", "None")
                }
            )
            
            results.append(character_arc)
            logger.info(f"Finished generating character arc for {name}")
    
    logger.info(f"Completed generation of {len(results)} character arcs")
    return results