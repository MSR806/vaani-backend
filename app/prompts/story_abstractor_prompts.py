# Prompts for StoryAbstractor

# Character Arc Abstraction Prompts
CHARACTER_ARC_SYSTEM_PROMPT = (
    "You are a narrative structure expert specializing in character arc abstraction. "
    "Your task is to transform a specific character's growth arc into a generalized, "
    "reusable template by abstracting away specific details while preserving the "
    "emotional and developmental journey."
)

CHARACTER_ARC_USER_PROMPT_TEMPLATE = (
    "Transform the following character growth analysis into a generalized character arc template:\n\n"
    "{character_growth}\n\n"
    "Follow these guidelines:\n"
    "1. Replace the specific character name with a general archetype (e.g., 'The Mentor', 'The Rebel')\n"
    "2. Preserve the nature of the relationship between the characters\n"
    "3. Preserve the emotional trajectory and core lessons learned\n"
    "4. Create a structure that could be applied to any story in the romance genre\n"
    "5. Preserve the Personality and the relationship dynamic between the characters\n"
    "Format the output as the source text\n"
    "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response. Provide the content directly in markdown format."
)

CHARACTER_ARC_BATCH_USER_PROMPT_TEMPLATE = (
    "Transform the following character growth analyses into generalized character arc templates.\n\n"
    "You MUST generate a template for EVERY character provided below. Do NOT skip any character, even if their arc seems incomplete.\n"
    "At the top of your response, list ALL character names as a checklist. Your response will be checked for every name.\n\n"
    "For each character, follow these guidelines:\n"
    "1. Replace the specific character name with a general archetype (e.g., 'The Mentor', 'The Rebel').\n"
    "2. Assign a role to each character (e.g., 'The Protagonist', 'The Antagonist', 'The Love Interest', etc.).\n"
    "3. The FIRST LINE of each template MUST be: # [Role] - [Archetype] (e.g., # The Antagonist - The Cunning Rival).\n"
    "4. Each template MUST include the following sections, in this order:\n"
    "   ## Description\n   [Include the character's personality, appearance, setting, backstory, and other relevant details]\n"
    "   ## Role\n   [Specify the character's role in the story (e.g., Female Protagonist, Antagonist, etc.). IMPORTANT: Do NOT generate a description, just generate a two-word phrase about the character.]\n"
    "   ## Key Relationships\n   [Describe the character's significant relationships with other characters in the story]\n"
    "   ## Motivation\n   [Explain the character's core drives and desires throughout the story]\n"
    "   ## Starting State\n   [Describe the character's initial condition, mindset, and relationships at the beginning]\n"
    "   ## Transformation\n   [Identify the key moments and catalysts that change the character throughout the story]\n"
    "   ## Ending State\n   [Describe the character's final state and how they've changed from their starting point]\n"
    "5. Preserve the nature of the relationship between the characters.\n"
    "6. Preserve the emotional trajectory and core lessons learned.\n"
    "7. Create a structure that could be applied to any story in the romance genre.\n"
    "8. Preserve the Personality and the relationship dynamic between the characters.\n\n"
    "Format your output as follows (see example):\n\n"
    "CHARACTER: [Original Character Name 1]\n"
    "FILE_START\n"
    "# The Antagonist - The Cunning Rival\n"
    "## Description\n[...summary...]\n"
    "## Role\nFemale Antagonist\n"
    "## Key Relationships\n[...summary...]\n"
    "## Motivation\n[...summary...]\n"
    "## Starting State\n[...summary...]\n"
    "## Transformation\n[...summary...]\n"
    "## Ending State\n[...summary...]\n"
    "FILE_END\n\n"
    "CHARACTER: [Original Character Name 2]\n"
    "FILE_START\n"
    "# The Protagonist - The Gentle Mentor\n"
    "## Description\n[...summary...]\n"
    "## Role\nMale Protagonist\n"
    "## Key Relationships\n[...summary...]\n"
    "## Motivation\n[...summary...]\n"
    "## Starting State\n[...summary...]\n"
    "## Transformation\n[...summary...]\n"
    "## Ending State\n[...summary...]\n"
    "FILE_END\n\n"
    "...and so on for each character.\n\n"
    "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response.\n"
    "Do NOT skip any character. If information is missing, make reasonable assumptions.\n\n"
    "Here are the character growth analyses to abstract:\n\n{character_growth_batch}"
)

# Plot Beats Abstraction Prompts
PLOT_BEATS_SYSTEM_PROMPT = (
    "You are a narrative structure expert specializing in plot abstraction. "
    "Your task is to transform specific plot beats into a generalized, "
    "reusable narrative skeleton by abstracting away specific details while "
    "preserving the dramatic structure and emotional impact."
)

PLOT_BEATS_USER_PROMPT_TEMPLATE = (
    "Transform the following plot beats into a generalized narrative skeleton:\n\n"
    "{content}\n\n"
    "Follow these guidelines:\n"
    "1. Replace specific character names with general roles or archetypes\n"
    "2. Preserve the emotional trajectory and narrative momentum\n"
    "3. Preserve the main genre as Romance, sub genre and trope. Ex: Billionare Romance, Mafia Romance, Contract Marriage, Slow burn Romanceetc.\n"
    "4. Identify the narrative function of each beat (e.g., 'introduces conflict', 'raises stakes')\n"
    "{character_map_text}\n"
    "Format the output as a markdown document with numbered beats and their narrative functions.\n\n"
    "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response."
)
