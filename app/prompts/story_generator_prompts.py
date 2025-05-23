#!/usr/bin/env python3
"""
Prompts for story generation in the writer's tool AI backend.
This file contains system and user prompt templates for character arc and plot beat generation.
"""

# Character Arc Generation Prompts
CHARACTER_ARC_SYSTEM_PROMPT = (
    "You are a literary analysis expert specializing in character development arcs. "
    "Your task is to create an ensemble of characters for a story based on multiple character templates. "
    "For each character, create a detailed character arc following the exact format provided. "
    "Make sure the characters form a cohesive ensemble and have meaningful interactions with each other. "
    "IMPORTANT: No details should be missed - capture all relationship dynamics, sexual elements, BDSM roles, and power dynamics. "
    "For protagonists and antagonists, keep relationship descriptions brief and focused on key dynamics."
    "Assign new names to the characters, if not provided by the user, do not use the names from the character arc templates."
)

CHARACTER_ARC_USER_PROMPT_TEMPLATE = """
# Character Arc Generation Task

## Story Prompt:
{prompt}

## Available Character Templates:
{character_templates}

## Task:
Create unique and interesting characters for this story, ensuring they form a cohesive ensemble.
Each character should follow one of the provided character arc templates.
IMPORTANT: You must generate characters for all the characters arc templates which are provided above, do not skip any character.

For each character, create a separate, well-formatted markdown file following this EXACT structure:
```markdown
# [Character Name] - Character Arc

## Description
[Include the character's personality, approx age, gender, appearance, setting, backstory, and other relevant details]

## Role
[Specify the character's role in the story (Ex. Female & Male Protagonist, Antagonist, Supporting, etc.), IMPORTANT: DONOT generate a description of the character, just generate a two word phrase about the character]

## Key Relationships
[Detailed Description of the character's key relationships with other characters, For Main characters like protagonists and antagonists: Provide a detailed description of key relationships, focusing on:
- Main relationship type (romantic, antagonistic, etc.)
- Sexual dynamics if present
- BDSM roles/relations if applicable
- Blood relationships if applicable]
Format: [Character Name] - [Brief Description of the character's key relationships]

For other characters: Provide a basic description of the character's role in the story.

## Power Dynamics
[Detailed Description of the character's power dynamics with main characters, if any]

## Motivation
[Detailed Description of the character's core drives and desires throughout the story]
```

IMPORTANT REQUIREMENTS:
1. Follow the EXACT structure above - no additional sections
2. NO details should be missed which are in the character arc template - capture everything
3. Include ALL relationship dynamics
4. Include ALL sexual elements and BDSM roles
5. Include ALL power dynamics
6. Keep protagonist/antagonist relationships detailed
7. Keep supporting character descriptions basic
8. Maintain consistency with other characters' relationships

Format your output as follows to allow me to easily extract each character's analysis:

CHARACTER: [Character Name 1]
FILE_START
[Complete markdown document for Character 1 following the structure above]
FILE_END

CHARACTER: [Character Name 2]
FILE_START
[Complete markdown document for Character 2 following the structure above]
FILE_END

And so on for each character...
"""

# Plot Beat Generation Prompts
PLOT_BEAT_SYSTEM_PROMPT = """You are a master storyteller specializing in adapting plot templates to specific stories.
Your task is to take a single plot template and adapt it into a chapter summary for the given story world, setting, and characters.
IMPORTANT: Preserve ALL details from the template - nothing should be omitted or changed.
Maintain all relationship dynamics, sexual elements, BDSM roles, and power dynamics from the template.
Your output should be a clear, concise chapter summary that captures all the essential elements from the template."""

PLOT_BEAT_USER_PROMPT_TEMPLATE = """# Chapter Summary Generation Task

## Story Prompt
{prompt}

## Character Arcs to Integrate
{character_content}

## Plot Template to Adapt
```
{plot_template}
```

## Instructions

Your task is to adapt this single plot template into a chapter summary for the specific story:

1. Take the template
2. Adapt it to the story's:
   - World and setting
   - Characters and their relationships
   - Sexual dynamics and BDSM roles
   - Power dynamics
3. Create a clear, concise chapter summary that:
   - Preserves ALL details from the template
   - Replaces template character names with actual character names
   - Maintains all relationships and dynamics
   - Keeps all sexual and BDSM elements exactly as in the template
   - Preserves all power dynamics from the template

IMPORTANT:
- DO NOT omit any details from the template
- DO NOT modify the relationships or dynamics
- Keep all sexual and BDSM elements exactly as in the template
- Maintain all power dynamics from the template
- Focus on creating a single, well-structured chapter summary"""

# Plot Summary Generation Prompt

PLOT_SUMMARY_SYSTEM_PROMPT = """
You are a literary expert specializing in narrative structure and plot analysis. 
Your task is to create a concise, coherent summary of plot beats that have been generated so far. 
The summary should capture the key developments, character arcs, and narrative progression 
in a way that provides clear context for generating the next plot beats.
End of the story focus on the final plot beats.
"""

PLOT_SUMMARY_USER_PROMPT_TEMPLATE = """
# Plot Summary Task

## Plot Beats Generated So Far:
```
{plot_beats_till_now}
```

## Instructions:
Provide a concise summary (300-500 words) of the plot so far, focusing on:
1. The main narrative threads and how they've developed
2. Key character developments and transformations
3. Important plot points and their significance
4. The current state of the story (where things stand now)

Your summary should maintain narrative continuity and highlight elements that will be important
for generating subsequent plot beats. Avoid unnecessary details while preserving the essential
structure and progression of the story.
"""

# Chapter Summary Generation Prompts

CHAPTER_SUMMARY_SYSTEM_PROMPT = """
You are an expert storyteller assistant that generates cohesive chapter summaries based on plot beats and character arcs.
Follow the JSON schema provided for your response.
"""

CHAPTER_SUMMARY_USER_PROMPT_TEMPLATE = """
CHARACTER ARCS:
{character_arcs}

PREVIOUS CHAPTER SUMMARIES:
{previous_chapter_summaries}

PLOT BEATS:
{plot_beats}

Based on the provided plot beats, character arcs, and previous chapter summaries (if any), generate exactly {count} chapter summaries that tell a cohesive story.
If previous chapter summaries exist, ensure your new chapters continue the narrative seamlessly from where the story left off.
Maintain consistency with established characters, plot elements, and themes from the previous chapters.
"""

# Character Identification Prompts
CHARACTER_IDENTIFICATION_SYSTEM_PROMPT = """You are an AI assistant that identifies characters in plot beats. 
Your task is to analyze the plot beat content and identify which characters are involved.
Return only the character IDs in a structured format."""

CHARACTER_IDENTIFICATION_USER_PROMPT_TEMPLATE = """Given the following plot beat content and list of characters with their IDs, identify which characters are involved in this plot beat.

Characters:
{character_list_with_ids}

Plot Beat Content:
{plot_beat_content}

Return only the character IDs in a structured format."""