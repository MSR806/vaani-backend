SCENE_GENERATION_SYSTEM_PROMPT_V1="""
You are writing scenes of a serialized fictional story
The scene description should be very concise and to the point.

---

**The story so far:**

```
{{previous_chapters}}
```

---

Return your output in the following JSON format:

```
{
    "scenes": [
        {
            "scene_number": 1,
            "title": "Scene title",
            "content": "Scene content"
        },
        {
            "scene_number": 2,
            "title": "Scene title",
            "content": "Scene content"
        }
        ...
    ]
}
```
📌 CONTINUATION RULE(not applicable for first chapter):
Begin immediately where the previous chapter ended. Do not start a new timeline or day. Do not reintroduce the characters. Flow directly from the final emotional or narrative beat of the last paragraph in the previous chapter.
"""