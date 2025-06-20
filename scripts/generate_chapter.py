import datetime
import json
import sys
import time

import requests

# API Base URL - assuming local development
API_BASE_URL = "http://localhost/vaani/api/v1"  # Update as needed

# Access token placeholder - User will update this
ACCESS_TOKEN = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ill3OGhmeWV2cjJneG9qY3oxMWIzeCJ9.eyJpc3MiOiJodHRwczovL2Rldi02bTN2N3RnaXZ1enJzNXdlLnVzLmF1dGgwLmNvbS8iLCJzdWIiOiJnb29nbGUtb2F1dGgyfDEwOTUwNjExNTIyMjY5ODE2MjY2NCIsImF1ZCI6WyI5YTI0NDkyZi04MDNjLTQ2MWMtYjA1MS1mMWRkN2NlM2M1MDQiLCJodHRwczovL2Rldi02bTN2N3RnaXZ1enJzNXdlLnVzLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NDg4Mzk1MDAsImV4cCI6MTc0ODkyNTkwMCwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkhXWFlNRHVsYXFxY3UzTTJmRHduZlJpU0NDUzRNUFN2IiwicGVybWlzc2lvbnMiOlsiYm9vazpkZWxldGUiLCJib29rOnJlYWQiLCJib29rOndyaXRlIiwic3RvcnlfYm9hcmQ6cmVhZCIsInN0b3J5X2JvYXJkOndyaXRlIiwidGVtcGxhdGU6cmVhZCIsInRlbXBsYXRlOndyaXRlIl19.DYmOSr6Ps2H0Dg_iM3nGoKPMtWvkrYxHh_TwW9Abv-DgxdRmw-avGYqRZpivkI-FZy-yi-5axBnXMY5S9SVraigIfb6gBsZb3qvfkVKok_-PqsyMXB06a4-61EZyuy923xZTEhq64-oZsJWAyXXE7GyAiB7eie__n4MbqkN8P7BMfGMxI8F-wny6QfOcVHIw5bTxZZP24HHbBGKE6lJQ9YAgCS5JV-x5Neqx3I9FcQIETEHY8i0pwQ5ZCvFHhCJ4w_h_G7gd1hqmBJVPCZ3akm-FtNBU7F-KMR_0TDwD3iZgBvH2sDxLh7DFjZ4gehLz6WUiestrK_zmAs1XIs-LvA"

# Headers for API requests
headers = {"Authorization": ACCESS_TOKEN, "Content-Type": "application/json"}

# Hardcoded book ID
BOOK_ID = 49  # Update with the appropriate book ID

# Configuration flags
SKIP_SCENE_GENERATION = False  # Set to True to skip scene generation

CHAPTERS_TO_GENERATE = [x for x in range(10, 20 + 1)]

# Global placeholders for prompts
SCENE_GENERATION_PROMPT = """
This is a web novel serialized fiction.
Generate 5 to 6 scenes based on the provided chapter summary in the same order as the chapter summary.
Each scene must include:
    •       A scene title
    •       A short description

Do not try to invent anything follow the chapter summary. Don't introduce new characters, use the characters from the chapter summary.
This chapter should maintain a sense of ongoing tension or development, not closure.

🌍 World Setting & Genre:
- Legal world setting.
- Contemporary Billionaire Romance, contract marriage, possessive husband
- Tone: Slow burn, emotionally intense, dramatic, and sensual
- Highly sexual and romantic events.
- Sexual desire, jealousy, vulnerability, and emotional conflict are central
- Physical intimacy should be emotionally charged and built through sustained tension (not rushed or purely physical)
- Scenes should feel intimate, sexual, cinematic, and high-stakes in both personal and professional contexts.
"""

CHAPTER_CONTENT_PROMPT = """
Generate a 1500-2000 word chapter based strictly on the scene breakdown provided.

> ⚠️ Do not invent scenes, characters, or details not specified in scenes.
> Every scene element given must be represented fully in the chapter.
> End the chapter where the scene ends do not add any extra content.

Character Introduction Instructions:
> Whenever introducing the main characters, for the first time, in a line or two describe their socaial status, professinal outlook.
> Whenever introducing a new side character, in a line or two describe backstory and relevance to the main characters.
---

🌍 World Setting & Genre:
- Legal world setting.
- Contemporary Billionaire Romance, contract marriage, possessive husband
- Tone: Slow burn, emotionally intense, dramatic, and sensual
- Highly sexual and romantic events.
- Sexual desire, jealousy, vulnerability, and emotional conflict are central
- Physical intimacy should be emotionally charged and built through sustained tension (not rushed or purely physical)
- Scenes should feel intimate, sexual, cinematic, and high-stakes in both personal and professional contexts.

---

Now begin the chapter.
"""


def get_all_chapters(book_id):
    start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}/chapters"
    print(f"API Request: GET {url}")
    response = requests.get(url, headers=headers)
    request_time = time.time() - start_time

    if response.status_code == 200:
        print(f"API Response: {response.status_code} (Time: {format_time_delta(request_time)})")
        return response.json()
    else:
        print(f"API Error: {response.status_code} (Time: {format_time_delta(request_time)})")
        print(response.text)
        return None


def get_chapter_scenes(book_id, chapter_id):
    # Get existing scenes for a chapter
    start_time = time.time()
    url = f"{API_BASE_URL}/scenes?chapter_id={chapter_id}"
    print(f"API Request: GET {url}")
    response = requests.get(url, headers=headers)
    request_time = time.time() - start_time

    if response.status_code == 200:
        scenes = response.json()
        print(f"API Response: {response.status_code} (Time: {format_time_delta(request_time)})")
        return scenes
    else:
        print(f"API Error: {response.status_code} (Time: {format_time_delta(request_time)})")
        print(response.text)
        return []


def create_scenes_for_chapter(book_id, chapter_id, chapter_number, user_prompt=""):
    # Check if scenes already exist for this chapter
    existing_scenes = get_chapter_scenes(book_id, chapter_id)
    if existing_scenes and len(existing_scenes) > 0 and SKIP_SCENE_GENERATION:
        print(
            f"Scenes already exist for Chapter {chapter_number} (ID: {chapter_id}). Skipping scene creation."
        )
        return True

    prompt_start_time = time.time()
    custom_prompt = user_prompt or SCENE_GENERATION_PROMPT

    prompt_prep_time = time.time() - prompt_start_time
    print(f"Prepared prompt in {format_time_delta(prompt_prep_time)}")

    # Make the API request
    api_start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}/generate-scenes"
    data = {"user_prompt": custom_prompt}
    print(f"API Request: POST {url}")
    response = requests.post(url, headers=headers, json=data)
    api_time = time.time() - api_start_time

    if response.status_code == 200:
        print(f"API Response: {response.status_code} (Time: {format_time_delta(api_time)})")
        print(f"Successfully created scenes for chapter {chapter_number}")
        return response.json()
    else:
        print(f"API Error: {response.status_code} (Time: {format_time_delta(api_time)})")
        print(f"Error creating scenes for chapter {chapter_number}: {response.status_code}")
        print(response.text)
        return None


def update_chapter_content(book_id, chapter_id, content):
    api_start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}"
    data = {"content": content}

    print(f"API Request: PUT {url} (updating chapter content)")
    response = requests.put(url, headers=headers, json=data)
    api_time = time.time() - api_start_time

    if response.status_code in [200, 201, 204]:
        print(
            f"API Response: {response.status_code} - Successfully updated chapter content (Time: {format_time_delta(api_time)})"
        )
        return True
    else:
        print(
            f"API Error: {response.status_code} - Failed to update chapter content (Time: {format_time_delta(api_time)})"
        )
        print(response.text)
        return False


def generate_chapter_content(book_id, chapter_id, chapter_number, user_prompt=""):
    prompt_start_time = time.time()
    custom_prompt = user_prompt or CHAPTER_CONTENT_PROMPT

    prompt_prep_time = time.time() - prompt_start_time
    print(f"Prepared content prompt in {format_time_delta(prompt_prep_time)}")

    api_start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}/generate-content"
    data = {"user_prompt": custom_prompt}

    print(f"API Request: POST {url} (streaming)")
    # Use stream=True for SSE response
    response = requests.post(url, headers=headers, json=data, stream=True)
    connection_time = time.time() - api_start_time
    print(f"Connection established in {format_time_delta(connection_time)}")

    streaming_start_time = time.time()
    if response.status_code == 200:
        print(f"API Response: {response.status_code} - Stream started")
        full_content = ""
        print(f"Receiving streamed content for chapter {chapter_number}...")

        chunk_count = 0
        # Process the SSE stream
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                # SSE format begins with 'data: '
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        print("\nStream completed.")
                        break

                    try:
                        # Parse the JSON data
                        data = json.loads(data_str)
                        if "content" in data:
                            content_chunk = data["content"]
                            full_content += content_chunk
                            chunk_count += 1

                            # Show a spinning loader animation
                            spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                            spinner_idx = chunk_count % len(spinner_chars)

                            # Every 25 chunks, update the counter
                            if chunk_count % 25 == 0:
                                progress_msg = f"\rGenerating content: {spinner_chars[spinner_idx]} {chunk_count} chunks | {len(full_content)} chars"
                            else:
                                progress_msg = f"\rGenerating content: {spinner_chars[spinner_idx]}"

                            sys.stdout.write(progress_msg)
                            sys.stdout.flush()
                        elif "error" in data:
                            print(f"\nError in stream: {data['error']}")
                    except json.JSONDecodeError:
                        print(f"\nInvalid JSON in data: {data_str}")

        streaming_time = time.time() - streaming_start_time
        words_count = len(full_content.split())
        content_size = len(full_content)

        # Clear the progress line
        sys.stdout.write("\r" + " " * 80 + "\r")

        # Print a nice summary
        print(f"Content generation stats:")
        print(f"  - Time: {format_time_delta(streaming_time)}")
        print(f"  - Chunks: {chunk_count}")
        print(f"  - Characters: {content_size:,d}")
        print(f"  - Words: ~{words_count:,d}")
        print(f"  - Generation speed: {int(content_size/streaming_time)} chars/sec")

        # Update the chapter content in the database
        print("Saving content to database...")
        update_result = update_chapter_content(book_id, chapter_id, full_content)

        if update_result:
            print("Successfully saved chapter content to database.")
        else:
            print("Warning: Generated content was not saved to the database!")

        return {"content": full_content}
    else:
        print(f"API Error: {response.status_code} (Time: {format_time_delta(connection_time)})")
        print(f"Error generating content for chapter {chapter_id}: {response.status_code}")
        print(response.text)
        return None


def format_time_delta(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def main():
    # Start overall timer
    overall_start_time = time.time()
    print(f"Started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Get all chapters for the book
    chapters_start_time = time.time()
    print(f"Getting all chapters for book {BOOK_ID}...")
    chapters = get_all_chapters(BOOK_ID)
    chapters_time = time.time() - chapters_start_time
    print(f"Retrieved chapters in {format_time_delta(chapters_time)}")

    if not chapters:
        print("No chapters found or error retrieving chapters.")
        return

    # Sort chapters by chapter number
    chapters.sort(key=lambda x: x.get("chapter_no", 0))

    # Process each chapter sequentially
    for chapter in chapters:
        chapter_id = chapter.get("id")
        chapter_no = chapter.get("chapter_no")
        chapter_title = chapter.get("title", "Untitled")
        if chapter_no not in CHAPTERS_TO_GENERATE:
            continue

        chapter_start_time = time.time()
        print(f"\nProcessing Chapter {chapter_no}: {chapter_title} (ID: {chapter_id})")

        # Step 1: Create scenes for the chapter (if not skipped)
        scenes_result = None
        if not SKIP_SCENE_GENERATION:
            scene_start_time = time.time()
            print(f"Creating scenes for chapter {chapter_id}...")
            scenes_result = create_scenes_for_chapter(BOOK_ID, chapter_id, chapter_no)
            scene_time = time.time() - scene_start_time
            print(f"Scene creation completed in {format_time_delta(scene_time)}")

            if not scenes_result:
                print(f"Skipping chapter {chapter_id} due to scene creation failure.")
                continue
        else:
            print("Scene generation skipped (SKIP_SCENE_GENERATION=True)")
            scenes_result = True  # Mark as successful to continue to content generation

        # Step 2: Generate chapter content without including scenes in the prompt
        content_start_time = time.time()
        print(f"Generating content for chapter {chapter_id}...")
        content_result = generate_chapter_content(BOOK_ID, chapter_id, chapter_no)
        content_time = time.time() - content_start_time
        print(f"Content generation completed in {format_time_delta(content_time)}")

        if not content_result:
            print(f"Failed to generate content for chapter {chapter_id}.")
            continue

        chapter_time = time.time() - chapter_start_time
        print(
            f"Successfully processed chapter {chapter_no}: {chapter_title} in {format_time_delta(chapter_time)}"
        )

        # Add a delay between chapters to avoid overwhelming the API
        delay_seconds = 2  # Hardcoded delay of 2 seconds
        print(f"Waiting {delay_seconds} seconds before processing next chapter...")
        time.sleep(delay_seconds)

    # Calculate and print overall time
    overall_time = time.time() - overall_start_time
    print(f"\nTotal execution time: {format_time_delta(overall_time)}")
    print(f"Finished at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    # Validate token
    if ACCESS_TOKEN == "YOUR_ACCESS_TOKEN_HERE":
        print("Please update the ACCESS_TOKEN variable in the script with your actual token.")
        sys.exit(1)

    # Run the main process
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError during execution: {str(e)}")
        sys.exit(1)
