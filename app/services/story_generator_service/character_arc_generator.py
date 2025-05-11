#!/usr/bin/env python3
import re
import logging
from sqlalchemy.orm import Session

# Import from app services
from app.services.ai_service import get_openai_client
from app.repository.story_board_repository import StoryBoardRepository
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.services.setting_service import get_setting_by_key
from app.utils.constants import SettingKeys
from app.models.enums import StoryBoardStatus

# Import prompt templates
from app.prompts.story_generator_prompts import (
    CHARACTER_ARC_SYSTEM_PROMPT,
    CHARACTER_ARC_USER_PROMPT_TEMPLATE
)

logger = logging.getLogger(__name__)

class CharacterArcGenerator:
    def __init__(self, db: Session, story_board_id: int):
        """Initialize the character arc generator with a book ID"""
        self.db = db
        self.story_board_id = story_board_id
        self.character_arc_repo = CharacterArcsRepository(self.db)
        self.story_board_repo = StoryBoardRepository(self.db)
        
        # Initialize AI client
        try:
            self.client = get_openai_client()
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI client: {str(e)}")
            self.client = None
    
    async def initialize(self):
        """Initialize templates and directories"""
        # Verify book template directory exists
        if self.story_board_id:
            self.story_board = self.story_board_repo.get_by_id(self.story_board_id)
        
        if self.story_board:
            self.character_arc_templates = self.character_arc_repo.get_by_type_and_source_id("TEMPLATE", self.story_board.template_id)
    
    def _extract_character_arcs_from_content(self, character_markdown_content: str) -> tuple:
        # Extract individual character files using regex pattern
        pattern = r"CHARACTER:\s*([^\n]+)\s*\nFILE_START\s*\n([\s\S]*?)\nFILE_END"
        matches = re.findall(pattern, character_markdown_content)
        
        logger.info(f"Found {len(matches)} character matches in the generated content")
        
        # Process all character sections at once
        character_arcs_data = []
        
        for name, content in matches:
            character_name = name.strip()
            character_content = content.strip()
            
            # Extract role from content
            role_pattern = r"## Role\s*\n([^#]*?)\n##"
            role_match = re.search(role_pattern, character_content)
            character_role = role_match.group(1).strip() if role_match else "Unknown"
            
            # Remove markdown code block delimiters if present
            character_content = re.sub(r'^```markdown\n', '', character_content)
            character_content = re.sub(r'\n```$', '', character_content)
            character_content = re.sub(r'^```\n', '', character_content)
            character_content = character_content.strip()
            
            # Add to batch data
            character_arcs_data.append({
                'content': character_content,
                'type': "STORY_BOARD",
                'source_id': self.story_board_id,
                'name': character_name,
                'role': character_role
            })
            
        return character_arcs_data
    
    async def generate_character_arcs(self):
        """Generate character arcs using the AI client"""
        if not self.client:
            raise ValueError("AI client not initialized")
        
        character_templates_str = "\n\n".join([f"### Template {i}:\n{template.content}" for i, template in enumerate(self.character_arc_templates)])
        
        try:
            response = self.client.chat.completions.create(
                model=get_setting_by_key(self.db, SettingKeys.CHARACTER_ARC_GENERATION_MODEL.value).value,
                messages=[
                    {"role": "system", "content": CHARACTER_ARC_SYSTEM_PROMPT},
                    {"role": "user", "content": CHARACTER_ARC_USER_PROMPT_TEMPLATE.format(prompt=self.story_board.prompt, character_templates=character_templates_str)}
                ],
                temperature=float(get_setting_by_key(self.db, SettingKeys.CHARACTER_ARC_GENERATION_TEMPERATURE.value).value),
            )
            
            # Extract and process character arcs from the generated content
            character_arcs_data = self._extract_character_arcs_from_content(response.choices[0].message.content)
            
            # Save all character arcs to the database in a single transaction
            if character_arcs_data:
                self.character_arc_repo.batch_create(character_arcs_data)
                logger.info(f"Stored {len(character_arcs_data)} character arcs in batch operation")
            else:
                logger.error("No character arcs generated")
                
            
        except Exception as e:
            logger.error(f"Error generating character arc for template {template.name}: {str(e)}")
                
        logger.info("Character arc generation completed")
    
    async def execute(self):
        await self.initialize()

        self.story_board_repo.update(self.story_board_id, status=StoryBoardStatus.CHARACTER_ARC_GENERATION_IN_PROGRESS)
        
        await self.generate_character_arcs()
        
        self.story_board_repo.update(self.story_board_id, status=StoryBoardStatus.CHARACTER_ARC_GENERATION_COMPLETED)
        
        logger.info(f"Character arc generation completed.")

