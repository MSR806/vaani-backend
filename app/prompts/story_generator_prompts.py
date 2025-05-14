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
    "Make sure the characters form a cohesive ensemble and have meaningful interactions with each other."
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

For each character, create a separate, well-formatted markdown file following this EXACT structure:
```markdown
# [Character Name] - Character Arc

## Description
[Include the character's personality, appearance, setting, backstory, and other relevant details]

## Role
[Specify the character's role in the story (protagonist, antagonist, supporting character, etc.)] IMPORTANT: DONOT generate a description of the character, just generate a two word phrase about the character]

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
PLOT_BEAT_SYSTEM_PROMPT = (
    "You are a master storyteller and narrative structure expert specializing in plot development. "
    "Your task is to create detailed plot beats for a story based on a template, character arcs, and a simple prompt. "
    "You may be creating either the beginning of a story or continuing an existing narrative. "
    "Design a cohesive narrative structure that allows all character arcs to develop naturally throughout the story, "
    "while maintaining the dramatic progression and emotional impact from the plot template. "
    "When continuing a story, ensure smooth continuity with the existing narrative."
    "Ensure that numbering is maintained for a continuing story."
)

PLOT_BEAT_USER_PROMPT_TEMPLATE = """
# Plot Beat Generation Task

## Story Prompt
{prompt}

## Character Arcs to Integrate
{character_content}

## Story Progress So Far
```
{plot_till_now}
```

## Plot Template to Apply
```
{plot_template}
```

## Instructions

You are generating plot beats for a PROGRESSING STORY. This means:

1. If the "Story Progress So Far" section is empty, this is the BEGINNING of the story. Create the initial plot beats.
2. If the "Story Progress So Far" section contains content, you are CONTINUING the story. Your plot beats should follow naturally from what has already happened.

Create detailed plot beats for the story based on the template, the story prompt, and the character arcs:

1. Transform the abstract plot template into a specific storyline that fits the prompt
2. Design key plot points that allow all characters to develop according to their arcs
3. Create natural connections and compelling interactions between the characters
4. Maintain the narrative structure from the template while adapting it to this specific story
5. Ensure continuity with any existing plot beats provided in "Story Progress So Far"
6. Replace the Archetype names with the actual character names
7. Don't add anything about the Story Progress So Far

Each plot beat must follow the exact format from the plot beat template.

Your plot outline should:
- Include EXACTLY the same number of plot beats as in the template, no more and no less
- Format each beat following the structure in the plot beat template
- Ensure each character's arc is incorporated meaningfully
- Create a coherent narrative flow from beginning to end
- Maintain continuity with previous plot beats when continuing the story also plot beat number should be progressive from previous plot beats
"""

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