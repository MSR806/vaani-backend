# Prompts for story extraction in the writer's tool AI backend.
# This file contains system and user prompt templates for character arc extraction and plot beat analysis.

# Character Arc Extraction Prompts
CHARACTER_ARC_EXTRACTION_SYSTEM_PROMPT = (
    "You are a literary analysis expert specializing in character identification and development arcs. "
    "First, identify the main characters in the story. Then, for each significant character, "
    "analyze their complete journey throughout the narrative, tracking their growth, changes, and "
    "development from beginning to end."
)

CHARACTER_ARC_EXTRACTION_USER_PROMPT_TEMPLATE = """
# Character Arc Extraction Task

## Book Information
Title: {book_title}
Author: {book_author}

## Chapter Summaries
```
{combined_summary}
```

## Analysis Instructions

Create individual markdown files for each IMPORTANT character in the story:

1. Include ONLY the most significant characters (those that drive the plot or undergo meaningful development)

2. For each character, create a separate, well-formatted markdown file following this EXACT structure:
```markdown
# [Character Name] - Character Arc Analysis

## Description
[Include the character's personality, appearance, setting, backstory, and other relevant details]

## Role
[Specify the character's role in the story (Female & Male Protagonist, Antagonist, etc.)]

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

3. Format your output as follows to allow me to easily extract each character's analysis:

CHARACTER: [Character Name 1]
FILE_START
[Complete markdown document for Character 1 following the structure above]
FILE_END

CHARACTER: [Character Name 2]
FILE_START
[Complete markdown document for Character 2 following the structure above]
FILE_END

And so on for each important character...

Be thorough but concise in your analysis. Focus on quality over quantity, and include only characters with significant development or importance to the story.
"""

# Plot Beat Analysis Prompts
PLOT_BEAT_ANALYSIS_SYSTEM_PROMPT = (
    "You are a literary analysis assistant specializing in identifying plot beats and narrative structure. "
    "Your task is to analyze the provided chapter summaries and extract key plot events, "
    "turning points, and narrative progression. Analyze how the narrative develops across "
    "these consecutive chapters, identifying key events and their significance to the overall story."
)

PLOT_BEAT_ANALYSIS_USER_PROMPT_TEMPLATE = """
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
   - Whether it represents exposition, rising action, conflict, climax, falling action, or resolution

3. Identify any major turning points in the story
4. Analyze how this section advances the overall narrative arc
5. Extract key themes and character developments
6. Identify any foreshadowing or setup for future events

Format your response as a cohesive narrative analysis with plot beats that span across chapters.
Do NOT organize by chapter numbers - treat this as a continuous story section.
"""

CHAPTER_SUMMARY_SYSTEM_PROMPT = (
    "You are a literary assistant specializing in precise chapter summarization. "
    "Your task is to create a concise summary of the chapter that captures all key story elements. "
    "Focus on preserving plot points, character actions, and significant developments. "
    "Your summary should maintain the narrative flow while condensing the content."
)

CHAPTER_SUMMARY_USER_PROMPT_TEMPLATE = """
# Chapter Summarization Task

## Chapter Information
Title: {chapter_title}
Chapter Number: {chapter_number}

## Content to Summarize
```
{chapter_content}
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
