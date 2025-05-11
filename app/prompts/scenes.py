SCENE_GENERATION_SYSTEM_PROMPT_V1="""
You are writing scenes of a serialized fictional story

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
"""