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
