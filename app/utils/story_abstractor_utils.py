#!/usr/bin/env python3
import asyncio
import json
import logging
import re
import traceback
from typing import List, Dict, Any, Optional

import json
from app.models.models import CharacterArc as CharacterArcModel
from app.schemas.character_arcs import CharacterArcContent, CharacterArc
from app.prompts.story_abstractor_prompts import CHARACTER_ARC_SYSTEM_PROMPT, CHARACTER_ARC_SINGLE_USER_PROMPT

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_character_name_mappings(character_names: List[str]) -> Dict[str, str]:
    mappings = {}
    for i, name in enumerate(character_names, 1):
        mappings[name] = f"char_{i}"
    
    logger.info(f"Character name mappings:\n{mappings}")
    logger.info(f"Created mappings for {len(mappings)} characters")
    return mappings


async def parse_character_content_json(character_name: str, content_json_str: str) -> List[CharacterArcContent]:
    try:
        # Parse the JSON string into a list of ChapterContent objects
        content_list = json.loads(content_json_str)
        chapter_contents: List[CharacterArcContent] = []
        
        for item in content_list:
            if 'chapter_range' in item and 'content' in item:
                chapter_content = CharacterArcContent(**item)
                chapter_contents.append(chapter_content)
        
        logger.info(f"Parsed {len(chapter_contents)} chapter contents for character {character_name}")
        return chapter_contents
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing content_json for {character_name}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error parsing content_json for {character_name}: {str(e)}")
        return []


async def abstract_character_chapter_content(character_arc_content: CharacterArcContent, original_name: str, abstract_name: str, all_character_mappings: Dict[str, str], client, model: str, temperature: float) -> Dict[str, Any]:
    system_prompt = CHARACTER_ARC_SYSTEM_PROMPT
    
    # Format all character mappings as a string for the prompt
    character_mappings_text = "\n".join([f"{original}: {abstract}" for original, abstract in all_character_mappings.items()])
    
    # Create the user prompt with all character mappings
    user_prompt = CHARACTER_ARC_SINGLE_USER_PROMPT.format(
        original_character_name=original_name,
        abstract_character_id=abstract_name,
        character_mappings=character_mappings_text,
        character_content=character_arc_content.content
    )
    
    try:
        # Make the API call
        response = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
        )
        
        abstraction = response.choices[0].message.content.strip()
        logger.info(f"Received abstraction for {original_name} ({abstract_name}), chapter range: {character_arc_content.chapter_range}")
        
        return {
            "chapter_range": character_arc_content.chapter_range,
            "abstract_content": abstraction,
            "original_name": original_name,
            "abstract_name": abstract_name
        }
    except Exception as e:
        logger.error(f"Error abstracting character chapter content for {original_name}: {str(e)}")
        return {
            "chapter_range": character_arc_content.chapter_range,
            "abstract_content": f"Error abstracting content: {str(e)}",
            "original_name": original_name,
            "abstract_name": abstract_name
        }


async def abstract_character_content_json(character_name: str, content_json: List[CharacterArcContent], abstract_name: str, all_character_mappings: Dict[str, str], client, model: str, temperature: float) -> List[Dict[str, Any]]:
    # Constants
    MAX_CONCURRENT_TASKS = 15  # Limit concurrent API calls

    # Parse the content_json string into ChapterContent objects
    chapter_contents = content_json
    
    logger.info(f"Processing {len(chapter_contents)} chapter segments for character {character_name} as {abstract_name}")
    
    # Create a semaphore to limit concurrent API calls
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    # Define a function to process each beat with the semaphore
    async def process_segment(idx: int, chapter_content: CharacterArcContent):
        async with semaphore:
            logger.info(f"Starting segment {idx+1}/{len(chapter_contents)} for character {character_name}")
            result = await abstract_character_chapter_content(
                chapter_content,
                character_name,
                abstract_name,
                all_character_mappings,
                client,
                model,
                temperature
            )
            logger.info(f"Completed segment {idx+1}/{len(chapter_contents)} for character {character_name}")
            return result
    
    # Create tasks for each chapter content with controlled concurrency
    tasks = [process_segment(i, content) for i, content in enumerate(chapter_contents)]
    
    # Execute all tasks concurrently with controlled concurrency
    abstractions = await asyncio.gather(*tasks)
    
    logger.info(f"Completed abstraction of {len(abstractions)} chapter segments for character {character_name}")
    
    return abstractions


async def process_character_abstractions(character_arcs: List[CharacterArc], client, model, temperature) -> List[Dict[str, Any]]:
    # Create character name mappings
    character_names = [arc.name for arc in character_arcs if arc.name]
    name_mappings = create_character_name_mappings(character_names)
    
    abstraction_tasks = {}
    for arc in character_arcs:
        abstract_name = name_mappings.get(arc.name)
        task = abstract_character_content_json(
            arc.name,
            arc.content_json,
            abstract_name,
            name_mappings,  # Pass all character mappings
            client,
            model,
            temperature
        )
        abstraction_tasks[arc.name] = task
    
    # Execute all abstraction tasks concurrently
    abstraction_results = {}
    
    if abstraction_tasks:
        # Get the names in a fixed order to match with results
        names = list(abstraction_tasks.keys())
        tasks = list(abstraction_tasks.values())
        
        # Execute all tasks concurrently
        all_abstractions = await asyncio.gather(*tasks)
        
        # Match results back to character names
        for i, name in enumerate(names):
            abstract_name = name_mappings.get(name)
            abstraction_results[name] = all_abstractions[i]
            logger.info(f"Finished abstracting all chapter segments for {name} as {abstract_name}")
    
    # Format results to match original content_json structure
    character_abstractions = []
    for name, abstractions in abstraction_results.items():
        abstract_name = name_mappings.get(name)
        
        # Create content_json format with abstracted segments
        content_json = []
        for chapter_abstraction in abstractions:
            content_json.append({
                "chapter_range": chapter_abstraction.get("chapter_range", ""),
                "content": chapter_abstraction.get("abstract_content", "")
            })
        
        character_abstractions.append({
            "name": name,
            "abstract_name": abstract_name,
            "content_json": content_json
        })
    
    logger.info(f"Completed all character abstractions")
    return character_abstractions