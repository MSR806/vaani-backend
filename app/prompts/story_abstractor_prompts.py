# Prompts for StoryAbstractor

# Character Arc Abstraction Prompts
CHARACTER_ARC_SYSTEM_PROMPT = (
    "You are a narrative structure expert specializing in character arc abstraction. "
    "Your task is to transform a specific character's details into a generalized, "
    "reusable template by abstracting away specific details while preserving the "
    "personality traits, relationships, and dynamics including sexual relationships, "
    "BDSM roles/relations, and power dynamics."
)

CHARACTER_ARC_BATCH_USER_PROMPT_TEMPLATE = (
    "Transform the following character analyses into generalized character arc templates.\n\n"
    "You MUST generate a template for EVERY character provided below. Do NOT skip any character.\n"
    "At the top of your response, list ALL character names as a checklist. Your response will be checked for every name.\n\n"
    "For each character, follow these guidelines:\n"
    "1. Replace the specific character name with a general archetype (e.g., 'The Mentor', 'The Rebel').\n"
    "2. Assign a role to each character (e.g., 'The Protagonist', 'The Antagonist', 'The Love Interest', etc.).\n"
    "3. The FIRST LINE of each template MUST be: # [Role] - [Archetype] (e.g., # The Antagonist - The Cunning Rival).\n"
    "4. Each template MUST include the following sections, in this order:\n"

    "## Description\n"
    "[Detailed Description of the character, Include the character's personality, approx age, gender, appearance, setting, backstory, and other relevant details]"
    ""
    "## Role"
    "[Specify the character's role in the story (Female & Male Protagonist, Antagonist, etc.), IMPORTANT: DONOT generate a description of the character, just generate a two word phrase about the character]"
    ""
    "## Key Relationships"
    "[Detailed Description of the character's key relationships with other characters, For Main characters like protagonists and antagonists: Provide a detailed description of key relationships, focusing on:"
    "- Main relationship type (romantic, antagonistic, etc.)"
    "- Sexual dynamics if present"
    "- BDSM roles/relations if applicable"
    "- Blood relationships if applicable]"
    "Format: [Character Name] - [Brief Description of the character's key relationships]"
    ""
    "For other characters: Provide a basic description of the character's role in the story, you can skip the non important characters."
    ""
    "## Power Dynamics"
    "[Detailed Description of the character's power dynamics with main characters, if any]"
    ""
    "## Motivation"
    "[Detailed Description of the character's core drives and desires throughout the story]"

    "5. Preserve the nature of the relationship between the characters, including sexual and power dynamics.\n"
    "6. Create a structure that could be applied to any story in the romance genre.\n"
    "7. Preserve the personality and all relationship dynamics between the characters.\n\n"

    "Format your output as follows (see example):\n\n"
    "CHARACTER: [Original Character Name 1]\n"
    "FILE_START\n"
    "# The Antagonist - The Cunning Rival\n"
    "## Description\n[...summary...]\n"
    "## Role\nFemale Antagonist\n"
    "## Key Relationships\n[...summary including sexual dynamics and power relationships where applicable...]\n"
    "## Motivation\n[...summary...]\n"
    "FILE_END\n\n"
    "CHARACTER: [Original Character Name 2]\n"
    "FILE_START\n"
    "# The Protagonist - The Gentle Mentor\n"
    "## Description\n[...summary...]\n"
    "## Role\nMale Protagonist\n"
    "## Key Relationships\n[...summary including sexual dynamics and power relationships where applicable...]\n"
    "## Motivation\n[...summary...]\n"
    "FILE_END\n\n"
    "...and so on for each character.\n\n"
    "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response.\n"
    "Do NOT skip any character. If information is missing, make reasonable assumptions.\n\n"
    "Here are the character analyses to abstract:\n\n{character_growth_batch}"
)

# Plot Beats Abstraction Prompts
PLOT_BEATS_SYSTEM_PROMPT = (
    "You are a narrative structure expert specializing in plot abstraction. "
    "Your task is to transform grouped chapter summaries into a generalized, "
    "reusable narrative skeleton by abstracting away specific details while "
    "preserving the narrative flow, emotional impact, and all relationship dynamics "
    "including sexual content, BDSM elements, and power dynamics."
)

PLOT_BEATS_USER_PROMPT_TEMPLATE = (
    "Transform the following grouped chapter summaries into a generalized narrative skeleton:\n\n"
    "{content}\n\n"
    "Follow these guidelines:\n"
    "1. Replace specific character names with general roles or archetypes\n"
    "2. Preserve the emotional trajectory and narrative momentum\n"
    "3. Preserve the main genre as Romance, sub genre and trope. Ex: Billionare Romance, Mafia Romance, Contract Marriage, Slow burn Romance, etc.\n"
    "4. Preserve ALL relationship dynamics including sexual relationships/attraction, sexual events, BDSM roles/relations, and power dynamics\n"
    "5. Create a cohesive narrative flow that maintains the original sequence of events\n"
    "{character_map_text}\n"
    "Format the output as a markdown document with paragraphs that follow the narrative flow.\n\n"
    "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response."
)