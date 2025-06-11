#!/usr/bin/env python3
import asyncio
import json
import logging
import re
import traceback
from typing import List, Dict

from app.models.models import Chapter
from app.services.ai_service import get_openai_client
from app.prompts.story_extractor_prompts import (
    CHARACTER_ARC_EXTRACTION_USER_PROMPT_TEMPLATE,
    CHARACTER_CONSOLIDATION_SYSTEM_PROMPT,
    CHARACTER_CONSOLIDATION_PROMPT_TEMPLATE
)
from app.schemas.character_arcs import (
    CharacterReference,
    CharacterArcNameGroups,
    CharacterArc,
    CharacterArcContent
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define constants
CHAPTER_BATCH_SIZE = 10  # Number of chapters to process per batch

async def process_chapter_batch_for_character_arcs(
    chapters: List[Chapter], 
    batch_number: int, 
    model_settings,
    client,
    system_prompt: str,
    template_book_title: str,
    template_author: str
) -> List[CharacterArc]:
    start_idx = (batch_number - 1) * CHAPTER_BATCH_SIZE
    end_idx = min(start_idx + CHAPTER_BATCH_SIZE, len(chapters))
    batch_chapters = chapters[start_idx:end_idx]
    
    if not batch_chapters:
        return []
    
    start_chapter_no = batch_chapters[0].chapter_no
    end_chapter_no = batch_chapters[-1].chapter_no
    chapter_range = [start_chapter_no, end_chapter_no]
    
    logger.info(f"Processing character arcs for chapters {start_chapter_no}-{end_chapter_no}")
    
    # Create combined summary from batch chapters
    combined_summary = ""
    for chapter in batch_chapters:
        if chapter.source_text:
            combined_summary += f"\n\nCHAPTER {chapter.chapter_no}: {chapter.title}\n{chapter.source_text}"
        else:
            logger.warning(f"No summary found for chapter {chapter.chapter_no}")
    
    if not combined_summary:
        logger.error(f"No chapter summaries available in batch {batch_number}")
        return []
    
    # Create prompt for character arc extraction
    user_prompt = CHARACTER_ARC_EXTRACTION_USER_PROMPT_TEMPLATE.format(
        book_title=template_book_title,
        book_author=template_author,
        combined_summary=combined_summary
    )
    
    try:
        # Get model and temperature from settings
        model, temperature = model_settings.extracting_character_arcs()
        logger.info(f"Making API call for batch {batch_number} using {model}")
        
        # Define a blocking function to wrap in asyncio.to_thread
        def blocking_openai_call():
            return client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
            )
        
        # Run the blocking call in a thread to avoid blocking the event loop
        response = await asyncio.to_thread(blocking_openai_call)
        
        character_markdown_content = response.choices[0].message.content
        
        # Extract individual character entries using regex
        pattern = re.compile(
            r"CHARACTER:\s*([^\n]+)\s*\n"        # name line
            r"FILE_START\s*\n"                   # allow spaces before the newline
            r"([\s\S]*?)"                        # block content (non-greedy)
            r"\s*FILE_END",                      # optional spaces before FILE_END
            re.DOTALL
        )
        
        # Find all matches
        matches = re.findall(pattern, character_markdown_content)
        logger.info(f"Found {len(matches)} characters in batch {batch_number}")
        
        # Create character arc entries with Pydantic models
        consolidated_characters = []
        role_pattern = r"## Role\n([^\n]+)"
        
        for name, content in matches:
            # Extract the role using regex
            role_match = re.search(role_pattern, content)
            role = role_match.group(1).strip() if role_match else ""
            
            # Extract Blood Relations section
            blood_relations_pattern = r"## Blood Relations\n([\s\S]*?)(?=\n## |\Z)"
            blood_relations_match = re.search(blood_relations_pattern, content)
            blood_relations = blood_relations_match.group(1).strip() if blood_relations_match else ""

            # Create a direct dictionary for content_json to use a list for chapter_range
            content_json_entry = {
                "chapter_range": chapter_range,  # List of 2 values [start, end]
                "content": content.strip(),
                "blood_relations": blood_relations
            }
            
            # Create consolidated character directly
            consolidated_character = CharacterArc(
                name=name.strip(),
                role=role,
                content_json=[CharacterArcContent(
                    chapter_range=chapter_range,
                    content=content.strip(),
                    blood_relations=blood_relations
                )]
            )
            consolidated_characters.append(consolidated_character)
        
        return consolidated_characters
    except Exception as e:
        logger.error(f"Error extracting character arcs for batch {batch_number}: {str(e)}")
        return []  # Empty list of ConsolidatedCharacter objects

async def get_consolidated_character_groups(
    character_references: List[CharacterReference],
    model_settings,
    client
) -> CharacterArcNameGroups:
    if not character_references:
        return CharacterArcNameGroups(groups=[])
    
    # Create a prompt for the LLM to identify duplicate characters AND provide canonical names
    character_refs_json = json.dumps([ref.model_dump() for ref in character_references], indent=2)
    consolidation_prompt = CHARACTER_CONSOLIDATION_PROMPT_TEMPLATE.format(character_references=character_refs_json)

    logger.info(f"Consolidating character references: {consolidation_prompt}")
    
    try:
        model, temperature = model_settings.extracting_character_arcs()
        
        # Use structured output parsing with the OpenAI beta API
        def blocking_structured_call():
            return client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": CHARACTER_CONSOLIDATION_SYSTEM_PROMPT},
                    {"role": "user", "content": consolidation_prompt}
                ],
                temperature=temperature,
                response_format=CharacterArcNameGroups
            )
        
        # Run the structured call in a thread
        completion = await asyncio.to_thread(blocking_structured_call)
        response = completion.choices[0].message.parsed
        logger.info(f"Used structured output parsing for consolidation")
        logger.info(f"Identified {len(response.groups)} unique characters across batches")
        return response
    except Exception as e:
        logger.error(f"Error consolidating characters: {str(e)}")
        logger.error(traceback.format_exc())
        return CharacterArcNameGroups(groups=[])

async def build_consolidated_characters(
    character_batches: List[List[CharacterArc]],
    character_groups: CharacterArcNameGroups
) -> List[CharacterArc]:
    # Create lookup dictionary for character access
    character_lookup: Dict[int, Dict[str, int]] = {}
    
    # Flatten characters and build lookup table
    for batch_idx, character_batch in enumerate(character_batches):
        for char_idx, character in enumerate(character_batch):
            index = len(character_lookup)
            character_lookup[index] = {
                "batch_idx": batch_idx,
                "char_idx": char_idx
            }
            
    if not character_groups.groups:
        return []
    
    consolidated_characters: List[CharacterArc] = []
    
    # Process each character group
    for group in character_groups.groups:
        # Skip groups without indices or canonical names
        if not group.indices or not group.canonical_name:
            continue
            
        # Create content_json array
        content_json_array: List[CharacterArcContent] = []
        
        # Extract role from first character
        first_idx = group.indices[0]
        first_lookup = character_lookup[first_idx]
        batch_idx = first_lookup["batch_idx"]
        char_idx = first_lookup["char_idx"]
        first_character = character_batches[batch_idx][char_idx]
        
        # Collect all content entries from the group
        for idx in group.indices:
            lookup = character_lookup[idx]
            batch_idx = lookup["batch_idx"]
            char_idx = lookup["char_idx"]
            char = character_batches[batch_idx][char_idx]
            
            # Process content_json from the ConsolidatedCharacter
            if char.content_json:
                # Add all entries from existing content_json
                for entry in char.content_json:
                    content_json_array.append(entry)
            else:
                # If no content_json, create a basic entry
                content_json_array.append({
                    "chapter_range": "Unknown",
                    "content": char.content
                })
        
        # Create the consolidated character directly using the collected content_json_array
        consolidated_character = CharacterArc(
            name=group.canonical_name,  # Use the LLM-suggested canonical name
            role=first_character.role,  # Keep the role from the first character occurrence
            content_json=content_json_array
        )
        
        # Keep as Pydantic model
        consolidated_characters.append(consolidated_character)
    
    return consolidated_characters


async def consolidate_character_arcs(
    character_batches: List[List[CharacterArc]],
    model_settings,
    client,
    mega_batch_size: int = 10  # Number of small batches per mega-batch
) -> List[CharacterArc]:
    if not character_batches or len(character_batches) == 0:
        return []
        
    logger.info(f"Starting hierarchical consolidation of {len(character_batches)} character batches")
    
    # Step 1: Group small batches into mega-batches
    mega_batches: List[List[List[CharacterArc]]] = []
    for i in range(0, len(character_batches), mega_batch_size):
        mega_batch = character_batches[i:i+mega_batch_size]
        mega_batches.append(mega_batch)
    
    logger.info(f"Created {len(mega_batches)} mega-batches from {len(character_batches)} original batches")
    
    # Step 2: Consolidate within each mega-batch
    mega_batch_results: List[List[CharacterArc]] = []
    for mb_idx, mega_batch in enumerate(mega_batches):
        logger.info(f"Consolidating characters within mega-batch {mb_idx+1}/{len(mega_batches)}")
        
        # Flatten the mega-batch
        flattened_mega_batch: List[CharacterArc] = [char for batch in mega_batch for char in batch]
        
        # Create character references for the flattened batch
        character_references: List[CharacterReference] = []
        for idx, character in enumerate(flattened_mega_batch):
            character_references.append(CharacterReference(
                index=idx,
                name=character.name
            ))
        
        # Get consolidated groups from LLM
        consolidated_groups = await get_consolidated_character_groups(
            character_references,
            model_settings,
            client
        )
        
        # Build consolidated characters from the groups
        consolidated_mega_batch = await build_consolidated_characters(
            [flattened_mega_batch],  # Pass as a single batch
            consolidated_groups
        )
        
        mega_batch_results.append(consolidated_mega_batch)
        logger.info(f"Mega-batch {mb_idx+1} consolidated: {len(consolidated_mega_batch)} unique characters")
    
    # Step 3: Final consolidation across all mega-batches
    if len(mega_batch_results) == 1:
        logger.info("Only one mega-batch, skipping final consolidation step")
        return mega_batch_results[0]
    
    logger.info(f"Performing final consolidation across {len(mega_batch_results)} mega-batches")
    
    # Create character references for final consolidation
    final_references: List[CharacterReference] = []
    final_characters_flat: List[CharacterArc] = []
    
    for batch in mega_batch_results:
        for character in batch:
            index = len(final_references)
            final_references.append(CharacterReference(
                index=index,
                name=character.name
            ))
            final_characters_flat.append(character)
    
    # Get final consolidated groups
    final_groups = await get_consolidated_character_groups(
        final_references,
        model_settings,
        client
    )
    
    # Build final consolidated characters
    final_characters = await build_consolidated_characters(
        [final_characters_flat],  # Treat as a single batch
        final_groups
    )
    
    logger.info(f"Final consolidation complete: {len(final_characters)} unique characters")
    return final_characters
