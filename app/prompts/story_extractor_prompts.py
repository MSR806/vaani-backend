# Prompts for story extraction in the writer's tool AI backend.
# This file contains system and user prompt templates for character arc extraction and plot beat analysis.

# Character Arc Extraction Prompts
CHARACTER_ARC_EXTRACTION_SYSTEM_PROMPT = (
    "You are a literary analysis expert specializing in character identification and development arcs. "
    "First, identify the main and supporting characters in the story. Then, for each character, "
    "extract their background, status, relationships, power dynamics, sexual relationship/attraction, BDSM roles/relations with other characters, and any other relevant details. "
    "For protagonists and antagonists, keep relationship descriptions brief and focused on key dynamics."
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

Create individual markdown files for each character in the story. Include all characters major and minor:

1. IMPORTANT: Extract all characters major and minor

2. For each character, create a separate, well-formatted markdown file following this EXACT structure:

# [Character Name] - Character Arc

## Description
[Detailed Description of the character, Include the character's personality, approx age, gender, appearance, setting, backstory, and other relevant details]

## Role
[Specify the character's role in the story (Female & Male Protagonist, Antagonist, etc.), IMPORTANT: DONOT generate a description of the character, just generate a two word phrase about the character]

## Key Relationships
[Detailed Description of the character's key relationships with other characters, For Main characters like protagonists and antagonists: Provide a detailed description of key relationships, focusing on:
- Main relationship type (romantic, antagonistic, etc.)
- Sexual dynamics if present
- BDSM roles/relations if applicable
- Blood relationships if applicable]
Format: [Character Name] - [Brief Description of the character's key relationships]

For other characters: Provide a basic description of the character's role in the story, you can skip the non important characters.

## Power Dynamics
[Detailed Description of the character's power dynamics with main characters, if any]

## Motivation
[Detailed Description of the character's core drives and desires throughout the story]

3. Format your output as follows to allow me to easily extract each character's analysis:

Format your output as follows (see example):
CHARACTER: [Character Name 1]
FILE_START
[Complete markdown document for Character 1 following the structure above]
FILE_END

CHARACTER: [Character Name 2]
FILE_START
[Complete markdown document for Character 2 following the structure above]
FILE_END

And so on for each important character...
"""

# Plot Beat Analysis Prompts
PLOT_BEAT_ANALYSIS_SYSTEM_PROMPT = (
    "You are a system that directly uses chapter summaries as plot beats. "
    "No additional processing or analysis is needed - the chapter summary will be used as-is."
)

PLOT_BEAT_ANALYSIS_USER_PROMPT_TEMPLATE = """
# Plot Beat Assignment

## Chapter Information
Chapter Number: {chapter_number}

## Chapter Summary
```
{chapter_summary}
```

The above chapter summary will be used directly as the plot beat for this chapter.
"""

CHAPTER_SUMMARY_SYSTEM_PROMPT = (
    "You are a literary assistant specializing in precise chapter summarization. "
    "Your task is to create a concise summary of the chapter that captures all key story elements. "
    "Focus on preserving plot points, character actions, and significant developments, sexual relationship/attraction, sexual events, BDSM roles/relations and power dynamics, etc."
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
5. Preserves sexual relationship/attraction, sexual events and BDSM roles/relations and power dynamics, etc.

Aim for a summary that is approximately 15-20% of the original length while ensuring everthing above is retained.
"""