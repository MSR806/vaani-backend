#!/usr/bin/env python3
import asyncio
import json
import re
import sys
import os
import time

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.database import get_db
from app.repository.book_repository import BookRepository
from app.repository.chapter_repository import ChapterRepository
from app.services.ai_service import get_openai_client
from app.utils.story_extractor_utils import (
    process_chapter_batch_for_character_arcs,
    consolidate_character_arcs,
)
from app.utils.model_settings import ModelSettings
from app.prompts.story_extractor_prompts import CHARACTER_ARC_EXTRACTION_SYSTEM_PROMPT

# Configuration variables
BOOK_ID = 21          # Book to process
CHAPTER_BATCH_SIZE = 10   # Number of chapters per batch
MEGA_BATCH_SIZE = 10      # Number of batches per mega-batch (10 batches x 10 chapters = 100 chapters)
MAX_CONCURRENT_TASKS = 15 # Maximum concurrent API calls

async def test_character_arc_consolidation(
    db: Session
):
    print(f"Testing character arc consolidation for book ID {BOOK_ID}")
    print(f"Using batch size: {CHAPTER_BATCH_SIZE} chapters")
    print(f"Using mega batch size: {MEGA_BATCH_SIZE} batches ({CHAPTER_BATCH_SIZE * MEGA_BATCH_SIZE} chapters total)")

    # Get book and chapters
    book_repo = BookRepository(db)
    book = book_repo.get_by_id(BOOK_ID)
    if not book:
        print(f"Book with ID {BOOK_ID} not found")
        return
    
    print(f"Found book: {book.title} by {getattr(book, 'author', 'Unknown author')}")
    
    chapter_repo = ChapterRepository(db)
    chapters = chapter_repo.get_by_book_id(BOOK_ID)
    chapters = [ch for ch in chapters if ch.source_text]  # Filter out chapters without summaries
    chapters.sort(key=lambda ch: ch.chapter_no)
    
    # only include 30 chapters
    chapters = chapters[:10]
    
    if not chapters:
        print("No chapters with summaries found for this book")
        return
        
    print(f"Found {len(chapters)} chapters with summaries")
    
    # Initialize OpenAI client and model settings
    client = get_openai_client()
    model_settings = ModelSettings(db)
    
    # Calculate number of batches needed
    num_batches = (len(chapters) + CHAPTER_BATCH_SIZE - 1) // CHAPTER_BATCH_SIZE
    print(f"Will process chapters in {num_batches} batches")
    
    # Process chapters in batches with controlled concurrency
    print("Processing chapter batches...")
    
    # Create a semaphore to limit concurrent tasks
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)  # Limit to MAX_CONCURRENT_TASKS concurrent tasks
    
    async def limited_batch_process(batch_num):
        async with semaphore:
            print(f"[START] Processing batch {batch_num}/{num_batches}")
            start_time = time.time()
            result = await process_chapter_batch_for_character_arcs(
                chapters=chapters,
                batch_number=batch_num,
                model_settings=model_settings,
                client=client,
                system_prompt=CHARACTER_ARC_EXTRACTION_SYSTEM_PROMPT,
                template_book_title=book.title,
                template_author=getattr(book, 'author', 'Unknown')
            )
            elapsed = time.time() - start_time
            print(f"[DONE] Batch {batch_num}/{num_batches} completed in {elapsed:.2f}s")
            return result
    
    # Create tasks with concurrency control
    print(f"[BATCH] Starting concurrent processing of {num_batches} batches...")
    batch_start = time.time()
    batch_tasks = [limited_batch_process(batch_num) for batch_num in range(1, num_batches + 1)]
    batch_results = await asyncio.gather(*batch_tasks)
    batch_elapsed = time.time() - batch_start
    print(f"[BATCH] All batches complete in {batch_elapsed:.2f}s")
    print(f"Completed processing {num_batches} batches of chapters")
    
    # Print summary of characters found in each batch
    for i, batch in enumerate(batch_results):
        start_idx = i * CHAPTER_BATCH_SIZE
        end_idx = min(start_idx + CHAPTER_BATCH_SIZE, len(chapters))
        print(f"Batch {i+1} (Chapters {chapters[start_idx].chapter_no}-{chapters[end_idx-1].chapter_no}): {len(batch)} characters")
        for char in batch:
            # Extract chapter range from content_json
            content_json = char.content_json
            chapter_ranges = [item.chapter_range for item in content_json] if content_json else []
            print(f"  - {char.name} (Chapters: {chapter_ranges[0] if chapter_ranges else 'Unknown'})")
    
    # Consolidate characters hierarchically
    print("\nPerforming hierarchical consolidation...")
    consolidation_start = time.time()
    consolidated_characters = await consolidate_character_arcs(
        character_batches=batch_results,
        model_settings=model_settings,
        client=client,
        mega_batch_size=MEGA_BATCH_SIZE
    )
    consolidation_elapsed = time.time() - consolidation_start
    print(f"Consolidation completed in {consolidation_elapsed:.2f}s")
    
    # Print consolidated characters
    print(f"\nAfter consolidation: {len(consolidated_characters)} unique characters")
    for char in consolidated_characters:
        content_json = char.content_json
        # Format chapter ranges for better readability
        chapter_ranges = []
        for item in content_json:
            if isinstance(item.chapter_range, list) and len(item.chapter_range) == 2:
                chapter_ranges.append(f"{item.chapter_range[0]}-{item.chapter_range[1]}")
            else:
                chapter_ranges.append(str(item.chapter_range))
        print(f"  - {char.name} (Role: {char.role or 'Unknown'})")
        print(f"    Appears in chapter ranges: {chapter_ranges}")
    
    # Save output to files
    print("\nSaving results to output files...")
    
    # Create output directory with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = f"character_arcs_output_{BOOK_ID}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")
    
    # Save consolidated characters as JSON
    consolidated_path = os.path.join(output_dir, "consolidated_characters.json")
    with open(consolidated_path, "w") as f:
        # Convert Pydantic models to dictionaries for JSON serialization
        characters_dict = [char.dict() for char in consolidated_characters]
        json.dump(characters_dict, f, indent=2)
    print(f"Saved consolidated characters to {consolidated_path}")
    
    # Save individual character files in markdown format
    characters_dir = os.path.join(output_dir, "characters")
    os.makedirs(characters_dir, exist_ok=True)
    
    for char in consolidated_characters:
        # Create a safe filename
        safe_name = re.sub(r'[^\w\s-]', '', char.name).strip().lower()
        safe_name = re.sub(r'[-\s]+', '-', safe_name)
        
        # Write markdown file
        md_filename = os.path.join(characters_dir, f"{safe_name}.md")
        with open(md_filename, "w") as f:
            content_json = char.content_json
            for item in content_json:
                # Format chapter range for better readability
                if isinstance(item.chapter_range, list) and len(item.chapter_range) == 2:
                    chapter_range = f"Chapters {item.chapter_range[0]}-{item.chapter_range[1]}"
                else:
                    chapter_range = f"Chapter {item.chapter_range}"
                
                f.write(f"### {chapter_range}\n")
                f.write(f"{item.content}\n\n")
    
    print(f"Saved {len(consolidated_characters)} individual character files to {characters_dir}/")

if __name__ == "__main__":
    # Get DB session
    db = next(get_db())
    
    # Run the test
    asyncio.run(test_character_arc_consolidation(db))
