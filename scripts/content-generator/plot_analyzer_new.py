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
PLOT_BEATS_MODEL = "gpt-4o-mini"  # For individual plot beat analysis (faster, cheaper)
SYNTHESIS_MODEL = "gpt-4o"    # For overall plot synthesis (better quality)

CHAPTER_SUMMARY_TEMPERATURE = 0.3
PLOT_BEATS_TEMPERATURE = 0.3
CHARACTER_GROWTH_TEMPERATURE = 0.3
PLOT_SUMMARY_TEMPERATURE = 0.3


class StoryAnalyzer:
    def __init__(self, book_id: int, db: Session):
        """Initialize the analyzer with a book ID and database session"""
        self.book_id = book_id
        self.db = db
        self.book = None
        self.chapters = []
        self.chapter_summaries = []
        self.characters = []
        
        # Set up directories
        self.output_dir = OUTPUT_DIR / f"book_{book_id}"
        self.summaries_dir = self.output_dir / "summaries"
        self.characters_dir = self.output_dir / "characters"
        self.plot_beats_dir = self.output_dir / "plot_beats"
        self.plot_structure_dir = self.output_dir / "plot_structure"
        self.character_growth_dir = self.output_dir / "character_growth"
        
        # Initialize with CHARACTER_MODEL as default, as it requires the highest capabilities
        self.client = get_openai_client(CHARACTER_MODEL)
        
        # Create output directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.characters_dir.mkdir(parents=True, exist_ok=True)
        self.plot_beats_dir.mkdir(parents=True, exist_ok=True)  
        self.plot_structure_dir.mkdir(parents=True, exist_ok=True)
        self.character_growth_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Log chapter titles
        for chapter in self.chapters:
            logger.info(f"Chapter {chapter.chapter_no}: {chapter.title}")
            
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
            
        # Create a simplified index file mapping chapter IDs to their titles
        chapter_index = {
            "book_id": self.book.id,
            "book_title": self.book.title,
            "chapters": {str(chapter.id): chapter.title for chapter in self.chapters}
        }
        
        # Save the index file
        index_path = self.output_dir / "index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(chapter_index, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Chapter index saved to {index_path}")
        
        return results
    
    async def _extract_characters_batch(self, combined_summaries: str) -> str:
        """Helper method to extract characters from a batch of summaries"""
        system_prompt = (
            "You are a literary analysis assistant specializing in character identification and analysis. "
            "Your task is to extract all character information from the provided chapter summaries. "
            "Focus on identifying characters who appear multiple times or play significant roles in the narrative. "
            "For each character, identify their full name, any aliases, their role in the story, and their "
            "key relationships to other characters."
        )
        
        user_prompt = f"""
        # Character Extraction Task
        
        ## Book Information
        Title: {self.book.title}
        Author: {self.book.author if hasattr(self.book, 'author') else 'Unknown'}
        
        ## Chapter Summaries
        ```
        {combined_summaries}
        ```
        
        ## Extraction Instructions
        
        1. Extract ALL named characters from these summaries
        2. For EACH character, provide:
           - Full name (if known)
           - Any aliases or alternative names
           - Their apparent role (protagonist, antagonist, supporting character, etc.)
           - Key relationships to other characters
           - Brief description based on available information
        
        3. Format your response as a structured list of characters with the requested information
        4. If the same character is referred to by different names, consolidate the information
        
Only include actual characters from the narrative, not mentioned historical figures or metaphorical entities.
"""
        
        try:
            logger.info(f"Making API call to extract characters using {CHARACTER_MODEL}")
            response = self.client.chat.completions.create(
                model=CHARACTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more factual extraction
            )
            
            return response.choices[0].message.content
        except Exception as e:
            error_message = f"Error extracting characters: {str(e)}"
            logger.error(error_message)
            return error_message
    
    async def extract_characters_from_summaries(self) -> Dict[str, Any]:
        """Extract character names from all chapter summaries using batching if necessary"""
        logger.info("Extracting characters from all chapter summaries")
        
        # Load all chapter summaries
        summaries = []
        for chapter in self.chapters:
            try:
                file_path = self.output_dir / f"chapter_{chapter.chapter_no}.md"
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
            logger.error("No chapter summaries found for character extraction")
            return {"error": "No summaries available"}
        
        logger.info(f"Loaded {len(summaries)} chapter summaries for character extraction")
        
        # We'll process all chapters in batches if there are many
        logger.info(f"Processing all {len(summaries)} chapter summaries for character extraction")
        
        # Determine if we need batching (over 15 chapters)
        BATCH_SIZE = 15
        character_analyses = []
        
        if len(summaries) <= BATCH_SIZE:
            # Small enough to process in one batch
            combined_summaries = "\n\n".join(
                [f"Chapter {s['chapter_no']}: {s['title']}\n{s['summary']}" 
                 for s in summaries]
            )
            character_analyses.append(await self._extract_characters_batch(combined_summaries))
        else:
            # Process in multiple batches
            batch_count = (len(summaries) + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division
            logger.info(f"Processing {len(summaries)} chapters in {batch_count} batches")
            
            for i in range(0, len(summaries), BATCH_SIZE):
                batch = summaries[i:i+BATCH_SIZE]
                logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{batch_count} (chapters {batch[0]['chapter_no']}-{batch[-1]['chapter_no']})")
                
                batch_summaries = "\n\n".join(
                    [f"Chapter {s['chapter_no']}: {s['title']}\n{s['summary']}" 
                     for s in batch]
                )
                batch_analysis = await self._extract_characters_batch(batch_summaries)
                character_analyses.append(batch_analysis)
        
        # Combine all character analyses
        character_analysis = "\n\n".join(character_analyses)
        
        # If we have multiple batches, we need to consolidate the characters
        if len(character_analyses) > 1:
            logger.info("Consolidating character information from multiple batches")
            
            # Create a consolidation prompt
            system_prompt = (
                "You are a literary analysis assistant specializing in character identification and consolidation. "
                "Your task is to consolidate character information from multiple analyses that may contain "
                "overlapping or contradictory information about the same characters. "
                "Create a unified, de-duplicated list of all characters with complete information."
            )
            
            user_prompt = f"""
            # Character Consolidation Task
            
            ## Book Information
            Title: {self.book.title}
            Author: {self.book.author if hasattr(self.book, 'author') else 'Unknown'}
            
            ## Multiple Character Analyses to Consolidate
            ```
            {character_analysis}
            ```
            
            ## Consolidation Instructions
            
            1. Review all character information across multiple analyses
            2. Identify and merge information about the same characters
            3. Resolve any contradictions in character information
            4. For EACH unique character, provide:
               - Full name (if known)
               - Any aliases or alternative names
               - Their apparent role (protagonist, antagonist, supporting character, etc.)
               - Key relationships to other characters
               - Brief description based on available information
            
            5. Format your response as a structured list of characters with the consolidated information
            
            Only include actual characters from the narrative, not mentioned historical figures or metaphorical entities.
            """
            
            try:
                # Make API call to consolidate characters
                logger.info(f"Making API call to consolidate character information using {CHARACTER_MODEL}")
                response = self.client.chat.completions.create(
                    model=CHARACTER_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,  # Lower temperature for more factual extraction
                )
                
                character_analysis = response.choices[0].message.content
            except Exception as e:
                logger.error(f"Error in character consolidation: {str(e)}")
                # Continue with the concatenated character analyses if consolidation fails
        
        try:
            # Save the raw character analysis to file
            characters_file = self.characters_dir / "characters_raw.md"
            with open(characters_file, 'w', encoding='utf-8') as f:
                f.write(character_analysis)
                
            logger.info(f"Character extraction saved to {characters_file}")
            
            # Also save as JSON for future processing
            characters_json = self.characters_dir / "characters.json"
            
            # Create a structured result
            result = {
                "book_id": self.book_id,
                "book_title": self.book.title,
                "character_analysis": character_analysis,
                "timestamp": int(time.time())
            }
            
            with open(characters_json, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Character data saved to {characters_json}")
            
            return result
            
        except Exception as e:
            error_message = f"Error extracting characters: {str(e)}"
            logger.error(error_message)
            return {"error": error_message}
    
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
                file_path = self.output_dir / f"chapter_{chapter.chapter_no}.md"
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
    
    async def analyze_character_growth(self, character_name: str) -> Dict[str, Any]:
        """Analyze growth for a character across chapter summaries"""
        logger.info(f"Analyzing character growth for: {character_name}")
        
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
            logger.error("No chapter summaries found for character analysis")
            return {"error": "No summaries available"}
            
        # Sort summaries by chapter number
        summaries.sort(key=lambda x: x["chapter_no"])
        
        # Combine summaries
        combined_summary = ""
        for summary in summaries:
            combined_summary += f"\n\nCHAPTER {summary['chapter_no']}: {summary['title']}\n{summary['summary']}"
        
        # Create prompts for character growth analysis
        system_prompt = (
            "You are a literary analysis expert specializing in character development and growth arcs. "
            "Your task is to analyze a specific character's journey throughout a story, tracking their "
            "emotional growth, behavioral changes, value shifts, and relationship development. Focus on "
            "identifying pivotal moments that transform the character and charting their overall arc "
            "from the beginning to the end of the story. You must provide a comprehensive analysis "
            "that covers ALL chapters, not just early chapters."
        )
        
        user_prompt = f"""
        # Character Growth Analysis Task
        
        ## Book Information
        Title: {self.book.title}
        Author: {self.book.author if hasattr(self.book, 'author') else 'Unknown'}
        
        ## Character to Analyze
        Character Name: {character_name}
        
        ## Chapter Summaries
        ```
        {combined_summary}
        ```
        
        ## Analysis Instructions
        
        IMPORTANT: Your analysis must cover the character's complete journey through ALL chapters, not just the early chapters. Make sure to include significant development in early, middle, AND late chapters with specific chapter references.
        
        1. Track {character_name}'s growth throughout the ENTIRE narrative by analyzing:
           - Emotional development (changes in attitudes, feelings, responses)
           - Behavioral patterns (how their actions/decisions evolve)
           - Value/belief systems (what matters to them and how that changes)
           - Skills and capabilities (what they learn to do)
           - Self-perception (how they view themselves)
        
        2. Identify key pivotal moments that transform the character across ALL chapters, including:
           - Challenges that force growth
           - Decisions that demonstrate character development
           - Interactions that change their perspective
           - Mistakes and learning moments
        
        3. Analyze relationship dynamics throughout the complete story:
           - How their relationships with other characters evolve from start to finish
           - How these relationships influence their growth
           - Patterns in forming new relationships
        
        4. Outline a complete character arc with specific chapter references:
           - Starting state (who they are at the beginning)
           - Transformation journey (key stages of development including early, middle, AND late chapters)
           - Ending state (who they become by the final chapters)
           - Thematic significance of their growth
        
        When referencing chapters, be specific (e.g., "In Chapters 31-40, Eva demonstrates...") and ensure you analyze development in late chapters with the same detail as early chapters.
        
        Format your response as a comprehensive analysis with clearly labeled sections for each aspect of character growth.
        """
        
        try:
            logger.info(f"Making API call to analyze character growth using {CHARACTER_MODEL}")
            response = self.client.chat.completions.create(
                model=CHARACTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=CHARACTER_GROWTH_TEMPERATURE,
            )
            
            character_analysis = response.choices[0].message.content
            
            # Save the character growth analysis to markdown file in the character_growth subfolder
            file_path = self.character_growth_dir / f"{character_name.replace(' ', '_').lower()}.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(character_analysis)
                
            logger.info(f"Character growth analysis saved to {file_path}")
            
            # Create a result dict with metadata
            result = {
                "character_name": character_name,
                "book_id": self.book_id,
                "book_title": self.book.title,
                "analysis": character_analysis,
                "timestamp": int(time.time())
            }
            
            return result
            
        except Exception as e:
            error_message = f"Error analyzing character growth for {character_name}: {str(e)}"
            logger.error(error_message)
            return {"error": error_message}
    
    async def extract_top_characters(self) -> List[str]:
        """Extract the main characters from the previously extracted character data"""
        try:
            # Try to load existing character data
            character_file = self.output_dir / "characters.json"
            if not character_file.exists():
                logger.error("No character data found. Run extract_all_characters first.")
                return []
            
            with open(character_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Use LLM to extract main character names from the character data
            system_prompt = (
                "You are a literary analysis assistant. Your task is to identify the main characters "
                "from a literary analysis of characters. Extract just the names of the 5-8 most "
                "significant characters based on their role and frequency of appearance in the story."
            )
            
            user_prompt = f"""
            # Main Character Identification Task
            
            ## Book Information
            Title: {self.book.title}
            
            ## Character Analysis Data
            ```
            {content}
            ```
            
            ## Instructions
            Identify the 5-8 most important characters from this analysis based on:
            1. Their role (protagonist, antagonist, major supporting character)
            2. Their apparent significance to the plot
            3. Their frequency of appearance or mention
            
            Return ONLY a comma-separated list of character names, nothing else.
            Example: "Character1, Character2, Character3, Character4, Character5"
            """
            
            response = self.client.chat.completions.create(
                model=CHARACTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse the comma-separated list
            character_names = [name.strip() for name in result.split(',')]
            logger.info(f"Extracted {len(character_names)} main characters: {', '.join(character_names)}")
            
            return character_names
        
        except Exception as e:
            logger.error(f"Error extracting main characters: {str(e)}")
            return []
    
    async def analyze_all_characters(self) -> List[Dict[str, Any]]:
        """Analyze all main characters for growth"""
        logger.info("Starting growth analysis for all main characters")
        
        # Step 1: Extract the main character names
        character_names = await self.extract_top_characters()
        
        if not character_names:
            logger.error("No main characters identified for analysis")
            return [{"error": "No characters to analyze"}]
        
        # Step 2: Analyze growth for each character
        all_results = []
        for name in character_names:
            logger.info(f"Analyzing character growth for: {name}")
            result = await self.analyze_character_growth(name)
            all_results.append(result)
            
            # Brief pause between analyses to avoid rate limits
            if name != character_names[-1]:  # Skip pause after the last character
                await asyncio.sleep(1)
        
        # Step 3: Save the character growth analysis index
        character_growth_index = {
            "book_id": self.book_id,
            "book_title": self.book.title,
            "character_count": len(all_results),
            "characters": [result["character_name"] for result in all_results if "error" not in result],
            "timestamp": int(time.time())
        }
        
        # Save the index file in the character_growth subfolder
        index_path = self.character_growth_dir / "index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(character_growth_index, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Character growth index saved to {index_path}")
        
        # Step 4: Generate relationship network analysis
        await self.analyze_character_relationships(character_names)
        
        return all_results
    
    async def analyze_character_relationships(self, character_names: List[str]) -> Dict[str, Any]:
        """Analyze the relationships between the main characters"""
        logger.info("Analyzing character relationship networks")
        
        # Check if we have all the individual character analyses first
        character_analyses = []
        for name in character_names:
            file_path = self.character_growth_dir / f"{name.replace(' ', '_').lower()}.md"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    character_analyses.append({
                        "name": name,
                        "analysis": f.read()
                    })
            else:
                logger.warning(f"Character analysis not found for {name}")
        
        if not character_analyses:
            logger.error("No character analyses found for relationship network analysis")
            return {"error": "No character analyses available"}
        
        # Combine the character analyses
        combined_analyses = ""
        for analysis in character_analyses:
            combined_analyses += f"\n\nCHARACTER: {analysis['name']}\n{analysis['analysis']}\n"
        
        # Create prompts for relationship network analysis
        system_prompt = (
            "You are a literary analysis expert specializing in character relationships and networks. "
            "Your task is to analyze how characters relate to each other throughout a narrative, identifying "
            "patterns of interaction, power dynamics, emotional connections, and how these relationships "
            "evolve over time. Focus on mapping the most significant relationship dynamics."
        )
        
        user_prompt = f"""
        # Character Relationship Analysis Task
        
        ## Book Information
        Title: {self.book.title}
        Author: {self.book.author if hasattr(self.book, 'author') else 'Unknown'}
        
        ## Character Analyses
        ```
        {combined_analyses}
        ```
        
        ## Main Characters
        {', '.join(character_names)}
        
        ## Analysis Instructions
        
        1. Map the key relationships between the main characters, including:
           - Family relationships
           - Romantic relationships
           - Friendships and alliances
           - Rivalries and conflicts
           - Mentor/mentee dynamics
           - Power dynamics
        
        2. For each significant relationship, analyze:
           - The initial state of the relationship
           - How it evolves throughout the story
           - Key moments that change the relationship
           - The final state of the relationship
        
        3. Identify relationship patterns across the narrative:
           - Recurring dynamics between different characters
           - How relationships influence character growth
           - How relationships drive plot developments
        
        4. Create a relationship network overview that shows:
           - The central relationships in the story
           - How relationships interconnect and influence each other
           - The thematic significance of the relationship dynamics
        
        Format your response as a comprehensive analysis that clearly maps the web of relationships 
        between characters and how they evolve throughout the narrative.
        """
        
        try:
            logger.info(f"Making API call to analyze character relationships using {CHARACTER_MODEL}")
            response = self.client.chat.completions.create(
                model=CHARACTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=CHARACTER_GROWTH_TEMPERATURE,
            )
            
            relationship_analysis = response.choices[0].message.content
            
            # Save the relationship analysis to markdown file in the character_growth subfolder
            file_path = self.character_growth_dir / "relationships.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(relationship_analysis)
                
            logger.info(f"Character relationship analysis saved to {file_path}")
            
            # Create a result dict with metadata
            result = {
                "book_id": self.book_id,
                "book_title": self.book.title,
                "characters": character_names,
                "analysis": relationship_analysis,
                "timestamp": int(time.time())
            }
            
            return result
            
        except Exception as e:
            error_message = f"Error analyzing character relationships: {str(e)}"
            logger.error(error_message)
            return {"error": error_message}

    
    async def synthesize_plot_summary(self) -> Dict[str, Any]:
        """Create an overall plot summary from all plot beat analyses"""
        logger.info("Synthesizing overall plot summary from all section analyses")
        
        # Collect all plot beat analysis files
        plot_beat_files = []
        for file in self.plot_beats_dir.glob("chapters_*_to_*.md"):
            if file.is_file():
                plot_beat_files.append(file)
        
        if not plot_beat_files:
            logger.error("No plot beat analysis files found for synthesis")
            return {"error": "No plot beat analyses available"}
        
        # Sort files by starting chapter number - filename format is 'plot_beats_chapters_X_to_Y.md'
        def extract_start_chapter(filename):
            try:
                # Split by underscore, get the part with the number, then extract just the number
                parts = filename.name.split('_')
                # The chapter number should be after 'chapters'
                for i, part in enumerate(parts):
                    if part == 'chapters' and i + 1 < len(parts):
                        return int(parts[i+1])
                return 0  # Default if pattern not found
            except (ValueError, IndexError):
                logger.warning(f"Could not extract chapter number from {filename}")
                return 0
                
        plot_beat_files.sort(key=extract_start_chapter)
        logger.info(f"Found {len(plot_beat_files)} plot beat section analyses")
        
        # Read the content of each file
        section_analyses = []
        for file in plot_beat_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    section_analyses.append({
                        "file": file.name,
                        "content": content
                    })
            except Exception as e:
                logger.error(f"Error reading plot beat file {file}: {str(e)}")
        
        if not section_analyses:
            logger.error("Failed to read any plot beat analysis content")
            return {"error": "Failed to read plot beat analyses"}
        
        # Combine the section analyses into a single input
        combined_analyses = ""
        for idx, analysis in enumerate(section_analyses):
            combined_analyses += f"\n\nSECTION {idx+1}: {analysis['file']}\n{analysis['content']}\n"
        
        # Create prompts for the overall synthesis
        system_prompt = (
            "You are a literary analysis expert specializing in narrative structure and plot development. "
            "Your task is to synthesize multiple section analyses into one cohesive overall plot structure "
            "for the entire story. Focus on extracting the major plot beats, turning points, character arcs, "
            "and thematic development that define the full narrative."
        )
        
        user_prompt = f"""
        # Overall Plot Synthesis Task
        
        ## Book Information
        Title: {self.book.title}
        Author: {self.book.author}
        
        ## Section Analyses
        {combined_analyses}
        
        ## Synthesis Instructions
        
        1. Identify major plot beats that form the backbone of the entire story
        2. For each major plot beat, provide:
           - A descriptive title for the plot development
           - A concise description of what happens
           - An analysis of its significance to the overall narrative
           - Where it fits in the story structure (exposition, rising action, climax, falling action, resolution)
        
        3. Identify the central conflicts and how they evolve through the story
        4. Describe the protagonist's journey and major character transformations
        5. Analyze 3-5 key themes that run throughout the narrative and how they develop
        6. Identify the major turning points that change the direction of the story
        
        Format your response as a comprehensive narrative analysis that provides a complete overview 
        of the story's structure, highlighting the major developments that drive the plot forward.
        """
        
        try:
            logger.info(f"Making API call to synthesize overall plot structure using {SYNTHESIS_MODEL}")
            response = self.client.chat.completions.create(
                model=SYNTHESIS_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,  # Lower temperature for more coherent analysis
            )
            
            overall_analysis = response.choices[0].message.content
            
            # Save the overall analysis to markdown file in the plot_structure subfolder
            file_path = self.plot_structure_dir / "overall.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(overall_analysis)
                
            logger.info(f"Overall plot structure analysis saved to {file_path}")
            
            # Create a result dict with metadata
            result = {
                "book_id": self.book_id,
                "book_title": self.book.title,
                "section_count": len(section_analyses),
                "overall_analysis": overall_analysis,
                "timestamp": int(time.time())
            }
            
            return result
            
        except Exception as e:
            error_message = f"Error synthesizing overall plot structure: {str(e)}"
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
        
        # Step 2: Check for existing character data
        characters_file = self.output_dir / "characters.json"
        if characters_file.exists():
            logger.info("Found existing character data")
            should_continue = input("Continue with existing character data? (y/n): ").strip().lower() == 'y'
            if not should_continue:
                logger.info("Re-extracting characters from summaries")
                await self.extract_characters_from_summaries()
        else:
            logger.info("No existing character data found")
            await self.extract_characters_from_summaries()
        
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
        
        # Step 4: Check for existing overall plot structure
        overall_structure_file = self.plot_structure_dir / "overall.md"
        if overall_structure_file.exists():
            logger.info("Found existing overall plot structure analysis")
            should_continue = input("Continue with existing overall plot structure? (y/n): ").strip().lower() == 'y'
            if not should_continue:
                logger.info("Re-synthesizing overall plot structure")
                await self.synthesize_plot_summary()
        else:
            # Re-check for plot beat files before synthesis
            plot_beat_files = list(self.plot_beats_dir.glob("chapters_*_to_*.md"))
            
            # Only offer to synthesize if we have plot beat analyses
            if plot_beat_files:
                logger.info(f"Found {len(plot_beat_files)} plot beat analyses for synthesis")
                should_synthesize = input("Proceed with overall plot structure synthesis? (y/n): ").strip().lower() == 'y'
                if should_synthesize:
                    await self.synthesize_plot_summary()
            else:
                logger.warning("Cannot synthesize overall plot structure without plot beat analyses")
        
        # Step 5: Check for existing character growth analysis
        character_growth_index = self.output_dir / "character_growth_index.json"
        if character_growth_index.exists():
            logger.info("Found existing character growth analyses")
            should_continue = input("Continue with existing character growth analyses? (y/n): ").strip().lower() == 'y'
            if not should_continue:
                logger.info("Re-analyzing character growth patterns")
                await self.analyze_all_characters()
        else:
            # Check for character data before offering character growth analysis
            characters_file = self.output_dir / "characters.json"
            if characters_file.exists():
                logger.info("Character data found for growth analysis")
                should_analyze_growth = input("Proceed with character growth analysis? (y/n): ").strip().lower() == 'y'
                if should_analyze_growth:
                    await self.analyze_all_characters()
            else:
                logger.warning("Cannot analyze character growth without character data")
        
        logger.info("Analysis completed")
        
        # Return a summary of what was generated
        return {
            "book_id": self.book_id,
            "book_title": self.book.title,
            "chapter_summaries": len(list(self.summaries_dir.glob("chapter_*.md"))),
            "character_data": characters_file.exists(),
            "plot_beat_analyses": len(plot_beat_files),
            "overall_plot_structure": overall_structure_file.exists(),
            "character_growth_analyses": len(list(self.character_growth_dir.glob("*.md"))),
            "character_relationships": (self.character_growth_dir / "relationships.md").exists(),
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
        analyzer = StoryAnalyzer(book_id, db)
        await analyzer.initialize()
        await analyzer.run_analysis()
        logger.info("Analysis completed successfully")
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
