CHAPTER_GENERATION_FROM_SCENE_SYSTEM_PROMPT_V1 = """
You are writing a chapter of a serialized fictional story

The story so far:

{{previous_chapters}}

⸻

Scene breakdown for the current chapter will be given by the user

Format each paragraph of your response with HTML paragraph tags with a style attribute for text alignment. Each new paragraph should be wrapped in its own tag. Example:
<p style="text-align:start">First paragraph content here.</p>
<p style="text-align:start">Second paragraph content here.</p>
"""