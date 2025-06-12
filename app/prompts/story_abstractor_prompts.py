# Prompts for StoryAbstractor

# Character Arc Abstraction Prompts
CHARACTER_ARC_SYSTEM_PROMPT = (
    "You are a narrative structure expert specializing in character arc abstraction. "
    "Your task is to transform a specific character's details into a generalized, "
    "reusable template by abstracting away specific details while preserving the "
    "personality traits, relationships, and dynamics including sexual relationships, "
    "BDSM roles/relations, and power dynamics."
)

# Blood Relations Abstraction Prompts
BLOOD_RELATIONS_SYSTEM_PROMPT = (
    "Replace character names with their abstract IDs in blood relations. Respond ONLY with the exact format requested and nothing else."
)

BLOOD_RELATIONS_USER_PROMPT = (
    "Mappings:\n{character_mappings}\n\n"
    "Blood Relations:\n{blood_relations}\n\n"
    "Replace names with IDs. Format: 'RelationType: ID'. If none, return only 'None'. Return nothing else - no explanations or extra text."
)

CHARACTER_ARC_SINGLE_USER_PROMPT = (
    "Transform the following character analysis into a generalized character arc template.\n\n"
    "Character name mappings:\n{character_mappings}\n\n"
    "You are working on the character: {original_character_name} = {abstract_character_id}\n\n"
    "Follow these guidelines:\n"
    "1. Use the provided numbered character identifier '{abstract_character_id}' instead of the original character name '{original_character_name}'.\n"
    "2. When referring to other characters in relationships, use their corresponding char_X identifiers from the mappings above.\n"
    "3. Assign a role to the character (e.g., 'The Protagonist', 'The Antagonist', 'The Love Interest', etc.).\n"
    "4. Preserve the nature of the relationship between the characters, including sexual and power dynamics.\n"
    "5. Create a structure that could be applied to any story in the romance genre.\n"
    "6. Preserve the personality and all relationship dynamics between the characters.\n\n"
    "7. Also preserve the nature of the profession or social status of the character. Ex. Very big CEO, rich man, ordinary, small job, etc.\n"
    "8. The FIRST LINE of the template MUST be: # [Specify the Role of the character] - [character identifier, Ex: char_X]\n"
    "Output format:\n\n"
    "## Description\n"
    "[Detailed Description of the character, Include the character's appearance, backstory, social status and other relevant details]"
    ""
    "## Role\n"
    "[Specify the character's role in the story (Female & Male Protagonist, Antagonist, etc.), IMPORTANT: DONOT generate a description of the character, just generate a two word phrase about the character]"
    ""
    "## Gender and age\n"
    "[Specify the character's gender and age if available, if not available, just skip this section]"
    "## Key Relationships\n"
    "[Detailed Description of the character's key relationships with other characters, For Main characters like protagonists and antagonists: Provide a detailed description of key relationships, focusing on:"
    "- Main relationship type (romantic, antagonistic, etc.)"
    "- Sexual dynamics if present"
    "- BDSM roles/relations if applicable"
    "Format: [Character Name] - [Brief Description of the character's key relationships]"
    ""
    "For other characters: Provide a basic description of the character's role in the story, you can skip the non important characters."
    ""
    "## Blood Relations\n"
    "[List all blood relatives of the character (parents, siblings, children, etc.), specifying their names and relationship to the character. If none, write 'None'.]"
    ""
    "## Power Dynamics\n"
    "[Detailed Description of the character's power dynamics with main characters, if any]"
    ""
    "## Motivation\n"
    "[Detailed Description of the character's core drives and desires throughout the story]"
    "IMPORTANT: There should not be any original character names in your output, only the provided character identifier ({abstract_character_id}) and references to other characters using their char_X identifiers.\n"
    "Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response.\n"
    "If information is missing, make reasonable assumptions based on what is provided.\n\n"
    "Here is the character arc to abstract:\n\n{character_content}"
)

# Plot Beats Abstraction Prompts
PLOT_BEATS_SYSTEM_PROMPT = (
    "You are a narrative structure expert specializing in plot abstraction. "
    "Your task is to transform chapter summaries into a generalized, "
    "reusable narrative skeleton by abstracting away specific details while "
    "preserving the narrative flow, emotional impact, and all relationship dynamics "
    "including sexual content, BDSM elements, and power dynamics. "
    "Abstract specific sensory or concrete details (e.g., objects, colors, brand names) into general terms, while preserving the emotional tone and core narrative events."
)

PLOT_BEATS_USER_PROMPT_TEMPLATE = (
    "Transform the following chapter summaries into a generalized narrative skeleton:\n\n"
    "{content}\n\n"
    "Follow these guidelines:\n"
    "1. Replace specific character names with the corresponding numbered identifiers (char_1, char_2, etc.)\n"
    "2. Preserve the emotional trajectory and narrative momentum\n"
    "3. Preserve the main genre as Romance, sub genre and trope. Ex: Billionare Romance, Mafia Romance, Contract Marriage, Slow burn Romance, etc.\n"
    "4. Preserve ALL relationship dynamics including sexual relationships/attraction, sexual events, BDSM roles/relations, and power dynamics\n"
    "5. Preserve any timeline related details like time of day, date, 3 weeks later, 6 months later, etc.\n"
    "6. Always preserve any professional details like transformation, job, etc.\n"
    "7. Create a cohesive narrative flow that maintains the original sequence of events\n\n"
    "{character_map_text}\n"
    "Format the output as a markdown document with paragraphs that follow the narrative flow.\n\n"
    "IMPORTANT: Do NOT wrap your response in markdown code blocks. Do not include ```markdown or ``` tags anywhere in your response."
)