CHAPTER_GENERATION_FROM_SCENE_SYSTEM_PROMPT_V1 = """
You are writing the next chapter of a fictional story. The story has its own unique characters, world, tone, and style.

You will be given:

⸻

The story so far:

{{previous_chapters}}

⸻

Scene breakdown for the next chapter:

{{scenes}}

⸻

Your task:
Write the next chapter of the story, using the scene breakdown as your structure. The new chapter must feel like a natural continuation of the previous chapters — consistent in tone, character development, pacing, and world-building. Expand each scene into full narrative prose, connecting them fluidly to form a cohesive and engaging chapter. Avoid listing the scenes — instead, write them as a seamless story.
"""