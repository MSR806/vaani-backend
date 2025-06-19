#!/usr/bin/env python3
"""
Prompts for story generation in the writer's tool AI backend.
This file contains system and user prompt templates for character arc and plot beat generation.
"""

# Character Arc Generation Prompts
CHARACTER_ARC_SYSTEM_PROMPT = (
    "You are a literary analysis expert specializing in character development arcs. "
    "Your task is to create a character arc for a story based on character template provided. "
    "Create a detailed character arc following the exact format provided. "
    "In the charcter arc template the charcters are referred with thier id, ex. char_1, char_2, char_3 etc. Replace the character id with the name of the character using the character mappings provided."
    "IMPORTANT: No details should be missed - capture all relationship dynamics, sexual elements, BDSM roles, and power dynamics. "
    "For protagonists and antagonists, keep relationship descriptions brief and focused on key dynamics."
    "If any world setting is provided, make sure the character arc is consistent with the world setting."
)

CHARACTER_ARC_USER_PROMPT_TEMPLATE = """
# Character Arc Generation Task

## Story Prompt:
{prompt}

## Character Arc Template:
{character_arc_template}

## Character Mappings:
{character_mappings}

## Task:
Create unique and interesting character arc for this story, ensuring they form a cohesive ensemble.
Character arc should follow the character arc template provided.

Output format:
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
Format: [Character Name] - [Brief Description of the character's key relationships]

## Blood Relationships
[Detailed Description of the character's blood relationships with other characters]

For other characters: Provide a basic description of the character's role in the story.

## Power Dynamics
[Detailed Description of the character's power dynamics with main characters, if any]

## Motivation
[Detailed Description of the character's core drives and desires throughout the story]

IMPORTANT REQUIREMENTS:
1. Follow the EXACT structure above - no additional sections other than the ones provided above
2. NO details should be missed which are in the character arc template - capture everything
3. Include ALL relationship dynamics
4. Include ALL sexual elements and BDSM roles
5. Include ALL power dynamics
6. Keep protagonist/antagonist relationships detailed
7. Keep supporting character descriptions basic
"""

# Character Arc Evolution Prompts
CHARACTER_ARC_EVOLUTION_USER_PROMPT_TEMPLATE = """
# Character Arc Evolution Task

## Story Prompt:
{prompt}

## Previous Character Arc:
{previous_character_arc}

## Character Arc Template for Current Chapter Range:
{character_arc_template}

## Character Mappings:
{character_mappings}

## Task:
Create a COMPLETE and SELF-CONTAINED character arc for the current chapter range that can stand independently while maintaining consistency with previous characterization.

## Dual Purpose Guidelines:
1. SELF-CONTAINED - The character arc MUST:
   - Include ALL essential character information needed for this chapter range
   - Provide COMPLETE descriptions of personality, relationships, and motivations
   - Be usable for story generation WITHOUT reference to previous arcs
   - Contain sufficient context about the character's current state

2. CONSISTENT FOUNDATION - While ensuring the arc is self-contained, maintain consistency in:
   - Core identity (name, gender, age)
   - Origin/background story
   - Blood relationships
   - Basic physical attributes
   - Professional skills/expertise

3. CURRENT DEVELOPMENT - Prioritize:
   - Character's current state appropriate to this chapter range
   - Recent developments in relationships and motivations
   - Present emotional state and goals
   - Natural evolution based on story events

Note: Current character's role in the template can be different from the previous arc. Ex. Male Antagonist can become Male Protagonist.

Output format:
# [Character Name] - Character Arc

## Description
[Complete description of the character as they exist in the current chapter range]

## Role
[Clear statement of the character's role]

## Gender and age
[Gender and age information]

## Key Relationships
[Comprehensive description of current relationships]

## Blood Relationships
[Complete information on blood relationships]

## Power Dynamics
[Current power dynamics in this chapter range]

## Motivation
[Complete description of the character's present motivations]

IMPORTANT REQUIREMENTS:
1. Follow the EXACT structure above
2. Ensure the arc is COMPLETE and can stand independently
3. Include ALL essential information needed for this chapter range
4. Maintain consistency with previous characterization while focusing on current development
5. The character arc must be immediately usable for story generation WITHOUT requiring previous arcs
"""

# Plot Beat Generation Prompts
PLOT_BEAT_SYSTEM_PROMPT = """You are a master storyteller specializing in adapting plot templates to specific stories.
Your task is to take a single plot template and adapt it into a chapter summary for the given story world, setting, and characters.
Your job is to generate a very crisp and concise 5-6 bullet points summary of the chapter.
The template may contain abstract character references like 'char_1', 'char_2', etc. Use the provided character name mappings to replace these with actual character names in your output.
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

## Character Name Mappings:
{character_mappings}

---

## Instructions

Your task is to adapt the summary template into the new world provided by the user and create a chapter summary for the story.

### You must do the following:

1. **IMPORTANT**: Replace all character references (char_1, char_2, etc.) with their actual names using the Character Name Mappings and Character Arcs above.

2. Adapt the summary template to reflect:
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

# Character Name Generation Prompt
CHARACTER_NAME_GENERATION_PROMPT = (
    "Generate realistic character names based on the following character templates.\n\n"
    "## Story Prompt:\n{prompt}\n\n"
    "Create names that would be appropriate for these characters. Consider the story prompt to ensure the names fit the story's setting, time period, and cultural context.\n"
    "Be creative but realistic - avoid fantasy names unless the character's description or story prompt explicitly suggests a fantasy setting.\n\n"
    "Character templates:\n{character_templates}\n\n"
    "Output format (IMPORTANT - return only the name mappings, nothing else):\n"
    "char_1 -> [Generated Name 1]\n"
    "char_2 -> [Generated Name 2]\n"
    "...\n"
)
