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
[Include the character's personality, appearance, backstory, profession, social status, and other relevant details]

## Role
[Specify the character's role in the story (Ex. Female & Male Protagonist, Antagonist, Supporting, etc.), IMPORTANT: DONOT generate a description of the character, just generate a two word phrase about the character]

## Gender and age
[Specify the character's gender and age if available, if not available, just skip this section]

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
Your job is to generate a very crisp and concise 5-6 bullet points summary of the chapter.
Also include a section listing all **characters involved**."""

PLOT_BEAT_USER_PROMPT_TEMPLATE = """# Chapter Summary Generation Task

## User Prompt
{prompt}

---

## Character Arcs:
{character_content}

---

## Summary Template to Adapt:
{plot_template}

---

## Instructions

Your task is to adapt the summary template into the new world provided by the user and create a chapter summary for the story.

### You must do the following:

1. Adapt the summary template to reflect:
   - The story's **world and setting**
   - The **characters** and their current relationships
   - **Sexual dynamics**, including **BDSM roles** (if any)
   - **Power dynamics** between characters

2. Write a **very crisp and concise chapter summary** in **5-6 bullet points**.  
Each bullet must:
- Describe one **key plot event** that occurs in the chapter.
- **Explicitly mention sexual or intimate events** (e.g., kissing, touching, sex) if they happen, using direct and bold language.
- Use **simple, clear phrasing** with no poetic or overly descriptive language.
- Preserve any timeline related details like time of day, date, 3 weeks later, 6 months later, etc.
- Always preserve any professional details like job, job transformations, etc.

3. Write a **BACKGROUND, EMOTION & CONTEXT** section.
This section is essential for informing full chapter generation later. It must include:
- Emotional tone and psychological state of characters in this chapter.
- Motivations, shifting dynamics, and narrative turning points.
- Power dynamics or role-based tension (e.g., dom/sub, boss/employee).
- Sexual energy, desire, tension, or release (if applicable).
- How this chapter fits into the broader story arc.

4. Include a **CHARACTERS INVOLVED** section.

---

### OUTPUT FORMAT:

**CHAPTER SUMMARY**
- [<Plot event 1>]
- [<Plot event 2>]
- [<Plot event 3>]
...

**BACKGROUND, EMOTION & CONTEXT**
- [Emotional tone of the chapter]
- [Character motivations and conflicts]
- [Power or sexual dynamics at play]
- [Narrative significance and turning points]
- [Setup for what might follow]

**CHARACTERS INVOLVED**
- [List of all named or meaningful characters present or referenced]
"""

# Character Identification Prompts
CHARACTER_IDENTIFICATION_SYSTEM_PROMPT = """You are an AI assistant that identifies characters in plot beats. 
Your task is to analyze the plot beat content and identify which characters are involved.
Return only the character IDs in a structured format."""

CHARACTER_IDENTIFICATION_USER_PROMPT_TEMPLATE = """Given the following chapter summary and list of characters with their IDs, identify which characters are involved in this chapter summary.

Characters:
{character_list_with_ids}

Chapter Summary:
{plot_beat_content}

Return only the character IDs in a structured format."""