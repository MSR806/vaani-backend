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
from app.models.models import Book, Chapter
from app.services.ai_service import get_openai_client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = Path(__file__).parent / "output"

# Hardcoded AI model settings
SUMMARY_MODEL = "gpt-4o-mini"  # For chapter summaries (faster, cheaper)
CHARACTER_MODEL = "gpt-4o"     # For character extraction (better quality)
PLOT_BEATS_MODEL = "gpt-4o"  # For individual plot beat analysis (faster, cheaper)

CHAPTER_SUMMARY_TEMPERATURE = 0.3
PLOT_BEATS_TEMPERATURE = 0.3
CHARACTER_GROWTH_TEMPERATURE = 0.3


class StoryExtractor:
    def __init__(self, book_id: int, db: Session):
        """Initialize the analyzer with a book ID and database session"""
        self.book_id = book_id
        self.db = db
        self.book = None
        self.chapters = []
        self.chapter_summaries = []
        self.characters = []
        
        # Set up directories
        self.output_dir = OUTPUT_DIR / f"book_{book_id}/analysis"
        self.summaries_dir = self.output_dir / "summaries"
        self.character_arcs_dir = self.output_dir / "character_arcs"  # Combined directory for character identity and growth
        self.plot_beats_dir = self.output_dir / "plot_beats"
        
        self.client = get_openai_client()
        
        # Create output directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.character_arcs_dir.mkdir(parents=True, exist_ok=True)
        self.plot_beats_dir.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Load book and chapters from database"""
        # Load book data
        self.book = self.db.query(Book).filter(Book.id == self.book_id).first()
        if not self.book:
            raise ValueError(f"Book with ID {self.book_id} not found")
        
        # Load chapters in order
        self.chapters = self.db.query(Chapter).filter(
            Chapter.book_id == self.book_id
        ).order_by(Chapter.chapter_no).all()
        
        # Double-check sorting to ensure chapters are in proper order
        self.chapters.sort(key=lambda chapter: chapter.chapter_no)
        
        if not self.chapters:
            raise ValueError(f"No chapters found for book with ID {self.book_id}")
        
        logger.info(f"Loaded book: {self.book.title}")
        logger.info(f"Found {len(self.chapters)} chapters")
            
        return self.book, self.chapters
    
    async def summarize_chapter(self, chapter: Chapter) -> Dict[str, Any]:
        """Summarize a single chapter while preserving key metadata and story elements"""
        logger.info(f"Summarizing Chapter {chapter.chapter_no}: {chapter.title}")
        logger.info(f"Using model: {SUMMARY_MODEL}, temperature: {CHAPTER_SUMMARY_TEMPERATURE}")
        
        system_prompt = (
            "You are a literary assistant specializing in precise chapter summarization. "
            "Your task is to create a concise summary of the chapter that captures all key story elements. "
            "Focus on preserving plot points, character actions, and significant developments. "
            "Your summary should maintain the narrative flow while condensing the content."
        )
        
        user_prompt = f"""
        # Chapter Summarization Task
        
        ## Chapter Information
        Title: {chapter.title}
        Chapter Number: {chapter.chapter_no}
        
        ## Content to Summarize
        ```
        {chapter.content}
        ```
        
        ## Summarization Instructions
        
        Please create a concise but comprehensive summary of this chapter that:
        
        1. Captures all key plot events in chronological order
        2. Identifies all characters who appear and their actions
        3. Preserves important dialogue and interactions
        4. Notes any character development or emotional changes
        5. Highlights setting changes or important locations
        6. Includes any foreshadowing or thematic elements
        
        Aim for a summary that is approximately 15-20% of the original length while ensuring no important story elements are lost.
        """
        
        try:
            # The OpenAI client doesn't return an awaitable in the newer version
            # We need to handle it properly without awaiting
            response = self.client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=CHAPTER_SUMMARY_TEMPERATURE,
            )
            
            summary_text = response.choices[0].message.content
            
            # Create summary with metadata (for tracking in memory)
            result = {
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "chapter_number": chapter.chapter_no,
                "original_length": len(chapter.content),
                "summary_length": len(summary_text),
                "summary": summary_text,
                "compression_ratio": len(summary_text) / (len(chapter.content) or 1),  # Avoid division by zero
                "timestamp": int(time.time())
            }
            
            # Save the summary text directly to a markdown file in the summaries subfolder
            file_path = self.summaries_dir / f"chapter_{chapter.chapter_no}.md"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(summary_text)
                
            logger.info(f"Summary saved to {file_path}")
            
            return result
        except Exception as e:
            error_message = f"Error summarizing chapter {chapter.id}: {str(e)}"
            logger.error(error_message)
            
            # Save error message to file for tracking
            file_path = self.summaries_dir / f"chapter_{chapter.chapter_no}.error.md"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(error_message)
            
            # Return error info for internal processing
            return {
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "chapter_number": chapter.chapter_no,
                "error": True
            }
    
    async def summarize_all_chapters(self) -> List[Dict[str, Any]]:
        """Summarize all chapters in the book"""
        # Process all chapters
        chapters_to_process = self.chapters
        logger.info(f"Summarizing all {len(chapters_to_process)} chapters")
        
        results = []
        for chapter in chapters_to_process:
            logger.info(f"Processing chapter {chapter.chapter_no}: {chapter.title}")
            result = await self.summarize_chapter(chapter)
            results.append(result)
            
        logger.info(f"All chapter summaries complete")
        
        return results
    
    # The extract_characters_from_summaries method has been removed as it's now part of extract_character_arcs
    
    async def analyze_plot_beats_batch(self, chapter_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze plot beats from multiple chapter summaries at once"""
        if not chapter_batch:
            logger.error("No chapters provided for batch plot analysis")
            return {"error": "No chapters provided"}
        
        # Get the range of chapters in this batch
        start_chapter = chapter_batch[0]["chapter_no"]
        end_chapter = chapter_batch[-1]["chapter_no"]
        logger.info(f"Analyzing plot beats for chapters {start_chapter} to {end_chapter}")
        
        # Combine the chapter summaries
        combined_summaries = ""
        for chapter in chapter_batch:
            combined_summaries += f"\n\nCHAPTER {chapter['chapter_no']}: {chapter['title']}\n{chapter['summary']}"
        
        system_prompt = (
            "You are a literary analysis assistant specializing in identifying plot beats and narrative structure. "
            "Your task is to analyze the provided chapter summaries and extract key plot events, "
            "turning points, and narrative progression. Analyze how the narrative develops across "
            "these consecutive chapters, identifying key events and their significance to the overall story."
        )
        
        user_prompt = f"""
        # Plot Beat Analysis Task
        
        ## Story Section Information
        Analyzing Story Section: Chapters {start_chapter} to {end_chapter}
        
        ## Chapter Summaries
        ```
        {combined_summaries}
        ```
        
        ## Analysis Instructions
        
        1. Identify 5-7 major plot beats across this entire story section (NOT organized by individual chapters)
        2. For EACH plot beat, provide:
           - A descriptive title for the plot development
           - A concise description of what happens
           - An analysis of its significance to the overall narrative
           - How it relates to character development or motivations
           - Whether it represents exposition, rising action, conflict, climax, falling action, or resolution
        
        3. Identify any major turning points in the story
        4. Analyze how this section advances the overall narrative arc
        5. Extract key themes and character developments
        6. Identify any foreshadowing or setup for future events
        
        Format your response as a cohesive narrative analysis with plot beats that span across chapters.
        Do NOT organize by chapter numbers - treat this as a continuous story section.
        """
        
        try:
            logger.info(f"Making API call to analyze plot beats for chapters {start_chapter}-{end_chapter} using {PLOT_BEATS_MODEL}")
            response = self.client.chat.completions.create(
                model=PLOT_BEATS_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=PLOT_BEATS_TEMPERATURE,
            )
            
            plot_analysis = response.choices[0].message.content
            
            # Save the batch plot analysis to markdown file in the plot_beats subfolder
            file_path = self.plot_beats_dir / f"chapters_{start_chapter}_to_{end_chapter}.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(plot_analysis)
                
            logger.info(f"Batch plot analysis saved to {file_path}")
            
            # Create a result dict with metadata
            result = {
                "start_chapter": start_chapter,
                "end_chapter": end_chapter,
                "chapters": [ch["chapter_no"] for ch in chapter_batch],
                "plot_analysis": plot_analysis,
                "timestamp": int(time.time())
            }
            
            return result
            
        except Exception as e:
            error_message = f"Error analyzing plot beats for chapters {start_chapter}-{end_chapter}: {str(e)}"
            logger.error(error_message)
            return {
                "start_chapter": start_chapter,
                "end_chapter": end_chapter,
                "error": error_message
            }
    
    async def analyze_all_plot_beats(self) -> List[Dict[str, Any]]:
        """Analyze all chapter summaries for plot beats using multi-chapter batches"""
        logger.info("Analyzing plot beats from all chapter summaries")
        
        # Load all chapter summaries
        summaries = []
        for chapter in self.chapters:
            try:
                file_path = self.summaries_dir / f"chapter_{chapter.chapter_no}.md"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        summary_text = f.read()
                        summaries.append({
                            "chapter_no": chapter.chapter_no,
                            "title": chapter.title,
                            "summary": summary_text
                        })
                else:
                    logger.warning(f"Summary file not found for chapter {chapter.chapter_no}")
            except Exception as e:
                logger.error(f"Error loading summary for chapter {chapter.chapter_no}: {str(e)}")
        
        if not summaries:
            logger.error("No chapter summaries found for plot beat analysis")
            return [{"error": "No summaries available"}]
        
        logger.info(f"Loaded {len(summaries)} chapter summaries for plot beat analysis")
        
        # Process in larger batches (10 chapters at a time for narrative continuity)
        BATCH_SIZE = 10  # Increased batch size to 10 as requested
        all_results = []
        
        batch_count = (len(summaries) + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division
        logger.info(f"Processing {len(summaries)} chapters in {batch_count} multi-chapter batches")
        
        for i in range(0, len(summaries), BATCH_SIZE):
            batch = summaries[i:i+BATCH_SIZE]
            start_ch = batch[0]['chapter_no']
            end_ch = batch[-1]['chapter_no']
            logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{batch_count} (chapters {start_ch}-{end_ch})")
            
            # Analyze this batch of chapters together
            batch_result = await self.analyze_plot_beats_batch(batch)
            all_results.append(batch_result)
            
            # Brief pause between batches to avoid rate limits
            if i + BATCH_SIZE < len(summaries):
                await asyncio.sleep(2)  # Slightly longer pause for larger batches
        
        # Save the full plot beat analysis index
        plot_beats_index = {
            "book_id": self.book_id,
            "book_title": self.book.title,
            "section_count": len(all_results),
            "sections": [
                {
                    "start_chapter": result["start_chapter"],
                    "end_chapter": result["end_chapter"],
                    "chapters": result["chapters"] if "chapters" in result else []
                } for result in all_results if "error" not in result
            ],
            "timestamp": int(time.time())
        }
        
        # Save the index file in the plot_beats subfolder
        index_path = self.plot_beats_dir / "index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(plot_beats_index, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Plot beats index saved to {index_path}")
        
        return all_results
    
    async def extract_character_arcs(self) -> Dict[str, Any]:
        """Extract character identities and their growth arcs in a single analysis pipeline"""
        logger.info("Extracting character arcs from chapter summaries")
        
        # Step 1: Load all chapter summaries
        summaries = []
        for chapter in self.chapters:
            try:
                file_path = self.summaries_dir / f"chapter_{chapter.chapter_no}.md"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        summary_text = f.read()
                        summaries.append({
                            "chapter_no": chapter.chapter_no,
                            "title": chapter.title,
                            "summary": summary_text
                        })
                else:
                    logger.warning(f"Summary file not found for chapter {chapter.chapter_no}")
            except Exception as e:
                logger.error(f"Error loading summary for chapter {chapter.chapter_no}: {str(e)}")
        
        if not summaries:
            logger.error("No chapter summaries found for character arc extraction")
            return {"error": "No summaries available"}
        
        logger.info(f"Loaded {len(summaries)} chapter summaries for character arc extraction")
        
        # Sort summaries by chapter number
        summaries.sort(key=lambda x: x["chapter_no"])
        
        # Step 2: Combine summaries
        combined_summary = ""
        for summary in summaries:
            combined_summary += f"\n\nCHAPTER {summary['chapter_no']}: {summary['title']}\n{summary['summary']}"
        
        # Step 3: Create prompts for character arc extraction
        system_prompt = (
            "You are a literary analysis expert specializing in character identification and development arcs. "
            "First, identify the main characters in the story. Then, for each significant character, "
            "analyze their complete journey throughout the narrative, tracking their growth, changes, and "
            "development from beginning to end."
        )
        
        user_prompt = f"""
        # Character Arc Extraction Task
        
        ## Book Information
        Title: {self.book.title}
        Author: {self.book.author if hasattr(self.book, 'author') else 'Unknown'}
        
        ## Chapter Summaries
        ```
        {combined_summary}
        ```
        
        ## Analysis Instructions
        
        Create individual markdown files for each IMPORTANT character in the story:
        
        1. Include ONLY the most significant characters (those that drive the plot or undergo meaningful development)
        
        2. For each character, create a separate, well-formatted markdown file following this EXACT structure:
        ```markdown
        # [Character Name] - Character Arc Analysis
        
        ## Description
        [Include the character's personality, appearance, setting, backstory, and other relevant details]
        
        ## Role
        [Specify the character's role in the story (protagonist, antagonist, supporting character, etc.)]
        
        ## Key Relationships
        [Describe the character's significant relationships with other characters in the story]
        
        ## Motivation
        [Explain the character's core drives and desires throughout the story]
        
        ## Starting State
        [Describe the character's initial condition, mindset, and relationships at the beginning]
        
        ## Transformation
        [Identify the key moments and catalysts that change the character throughout the story]
        
        ## Ending State
        [Describe the character's final state and how they've changed from their starting point]
        ```

        3. Format your output as follows to allow me to easily extract each character's analysis:

        CHARACTER: [Character Name 1]
        FILE_START
        [Complete markdown document for Character 1 following the structure above]
        FILE_END

        CHARACTER: [Character Name 2]
        FILE_START
        [Complete markdown document for Character 2 following the structure above]
        FILE_END

        And so on for each important character...
        
        Be thorough but concise in your analysis. Focus on quality over quantity, and include only characters with significant development or importance to the story.
        """
        
        try:
            logger.info(f"Making API call to extract character arcs using {CHARACTER_MODEL}")
            response = self.client.chat.completions.create(
                model=CHARACTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=CHARACTER_GROWTH_TEMPERATURE,
            )
            
            character_markdown_content = response.choices[0].message.content
            
            # Save the complete character arc analysis
            complete_analysis_path = self.character_arcs_dir / "complete_character_arcs.md"
            with open(complete_analysis_path, 'w', encoding='utf-8') as f:
                f.write(character_markdown_content)
            
            logger.info(f"Complete character arc analysis saved to {complete_analysis_path}")
            
            # Extract individual character files using regex pattern
            import re
            pattern = r"CHARACTER:\s*([^\n]+)\s*\nFILE_START\n([\s\S]*?)\nFILE_END"
            matches = re.findall(pattern, character_markdown_content)
            
            # Save individual character arc files
            character_names = []
            for name, content in matches:
                character_name = name.strip()
                character_names.append(character_name)
                character_filename = character_name.lower().replace(' ', '_').replace('"', '').replace("'", "") + ".md"
                file_path = self.character_arcs_dir / character_filename
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                
                logger.info(f"Character arc for {character_name} saved to {file_path}")
            
            # Create and save index file
            character_arc_index = {
                "book_id": self.book_id,
                "book_title": self.book.title,
                "character_count": len(character_names),
                "characters": character_names,
                "timestamp": int(time.time())
            }
            
            index_path = self.character_arcs_dir / "character_arcs_index.json"
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(character_arc_index, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Character arc index saved to {index_path}")
            
            return character_arc_index
            
        except Exception as e:
            error_message = f"Error extracting character arcs: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return {"error": error_message}

    
    async def save_text_file(self, text: str, filename: str) -> Path:
        """Save text content to a file"""
        file_path = self.output_dir / filename
        
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save text content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
                
            logger.info(f"Text saved to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving text file: {str(e)}")
            return None
    
    async def check_summaries_exist(self) -> bool:
        """Check if chapter summaries already exist"""
        # Sample a few chapters to check if summaries exist
        sample_chapters = self.chapters[:5] if len(self.chapters) >= 5 else self.chapters
        existing_count = 0
        
        for chapter in sample_chapters:
            file_path = self.output_dir / f"chapter_{chapter.chapter_no}.txt"
            if file_path.exists():
                existing_count += 1
        
        # If most sampled chapters have summaries, assume all do
        return existing_count >= len(sample_chapters) * 0.8
        
    async def check_characters_exist(self) -> bool:
        """Check if character extraction already exists"""
        # Check for both raw and structured character files
        characters_raw = self.characters_dir / "characters_raw.md"
        characters_json = self.characters_dir / "characters.json"
        
        return characters_raw.exists() and characters_json.exists()
    
    async def run_analysis(self) -> Dict[str, Any]:
        """Run the full analysis pipeline"""
        logger.info(f"Starting analysis for book ID: {self.book_id}")
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Check for existing chapter summaries
        existing_summaries = False
        for chapter in self.chapters:
            file_path = self.summaries_dir / f"chapter_{chapter.chapter_no}.md"
            if file_path.exists():
                existing_summaries = True
                break
        
        if existing_summaries:
            logger.info("Found existing chapter summaries")
            should_continue = input("Continue with existing summaries? (y/n): ").strip().lower() == 'y'
            if not should_continue:
                logger.info("Re-generating chapter summaries")
                await self.summarize_all_chapters()
        else:
            logger.info("No existing summaries found")
            await self.summarize_all_chapters()
        
        # Step 2: Check for existing character arc data
        character_arc_index = self.character_arcs_dir / "character_arcs_index.json"
        if character_arc_index.exists():
            logger.info("Found existing character arc analysis")
            should_continue = input("Continue with existing character arc analysis? (y/n): ").strip().lower() == 'y'
            if not should_continue:
                logger.info("Re-extracting character arcs from summaries")
                await self.extract_character_arcs()
        else:
            logger.info("No existing character arc analysis found")
            should_analyze_characters = input("Proceed with character arc extraction? (y/n): ").strip().lower() == 'y'
            if should_analyze_characters:
                await self.extract_character_arcs()
        
        # Step 3: Check for existing plot beat analyses
        plot_beat_files = list(self.plot_beats_dir.glob("chapters_*_to_*.md"))
        if plot_beat_files:
            logger.info(f"Found {len(plot_beat_files)} existing plot beat analyses")
            should_continue = input("Continue with existing plot beat analyses? (y/n): ").strip().lower() == 'y'
            if not should_continue:
                logger.info("Re-analyzing plot beats")
                await self.analyze_all_plot_beats()
        else:
            logger.info("No existing plot beat analyses found")
            should_analyze_plot = input("Proceed with plot beat analysis? (y/n): ").strip().lower() == 'y'
            if should_analyze_plot:
                await self.analyze_all_plot_beats()
                # Refresh the list of plot beat files after analysis
                plot_beat_files = list(self.plot_beats_dir.glob("chapters_*_to_*.md"))
        
        logger.info("Analysis completed")
        
        # Return a summary of what was generated
        return {
            "book_id": self.book_id,
            "book_title": self.book.title,
            "chapter_summaries": len(list(self.summaries_dir.glob("chapter_*.md"))),
            "character_arcs": len(list(self.character_arcs_dir.glob("*.md"))) - 1,  # Subtract 1 to account for the complete_character_arcs.md file
            "plot_beat_analyses": len(plot_beat_files),
            "output_directory": str(self.output_dir)
        }

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python plot_analyzer_new.py <book_id>")
        sys.exit(1)
        
    book_id = int(sys.argv[1])
    logger.info(f"Starting analysis for book ID: {book_id}")
    
    # Get database session
    db = next(get_db())
    
    try:
        analyzer = StoryExtractor(book_id, db)
        await analyzer.initialize()
        await analyzer.run_analysis()
        logger.info("Analysis completed successfully")
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
