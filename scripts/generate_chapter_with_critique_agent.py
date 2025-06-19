import requests
import json
import time
import sys
import datetime
import os
from keys import ACCESS_TOKEN

# API Base URL - assuming local development
API_BASE_URL = "http://localhost/vaani/api/v1"  # Update as needed

# Headers for API requests
headers = {"Authorization": ACCESS_TOKEN, "Content-Type": "application/json"}

# Hardcoded book ID - update as needed
BOOK_ID = 67

# Chapters to process - update as needed
CHAPTERS_TO_PROCESS = [x for x in range(1, 1 + 1)]

# Whether to update the chapter content in the database
UPDATE_DATABASE = True

# Create scenes for chapters without scenes
CREATE_SCENES = True

# Enable rewriting after generating
ENABLE_REWRITE = True

SCENE_GENERATION_PROMPT = """
This is a web novel serialized fiction.
Generate 5 to 6 scenes based on the provided chapter summary in the same order as the chapter summary.
Each scene must include:
    •       A scene title
    •       A short description

Do not try to invent anything follow the chapter summary. Don't introduce new characters, use the characters from the chapter summary.
This chapter should maintain a sense of ongoing tension or development, not closure.
Don't miss any details, background, sexual events, BDSM roles/relations and power dynamics, etc. from the current chapter summary.

🌍 World Setting & Genre:
- Contemporary Billionaire Romance, contract marriage, possessive husband
- Tone: Slow burn, emotionally intense, dramatic, and sensual
- Highly sexual and romantic events, BDSM roles involved.
- Sexual desire, jealousy, vulnerability, and emotional conflict are central
- Physical intimacy should be emotionally charged and built through sustained tension (not rushed or purely physical)
- Scenes should feel intimate, sexual, BDSM roles involved, cinematic, and high-stakes in both personal and professional contexts.
- Everything is grandeur to max extent to add serialise drama.
"""

CHAPTER_CONTENT_PROMPT = """
Generate a 1500-2000 word chapter based strictly on the scene breakdown provided.

> ⚠️ Do not invent scenes, characters, or details not specified in scenes.
> Every scene element given must be represented fully in the chapter.
> End the chapter where the scene ends do not add any extra content.

---

🌍 World Setting & Genre:
- Contemporary Billionaire Romance, contract marriage, possessive husband
- Tone: Slow burn, emotionally intense, dramatic, and sensual
- Highly sexual and romantic events, BDSM roles involved.
- Sexual desire, jealousy, vulnerability, and emotional conflict are central
- Physical intimacy should be emotionally charged and built through sustained tension (not rushed or purely physical)
- Scenes should feel intimate, sexual, BDSM roles involved, cinematic, and high-stakes in both personal and professional contexts.
- Everything is grandeur to max extent to add serialise drama.

---

Now begin the chapter.
"""

# Base save directory for HTML reports
BASE_SAVE_DIR = "/Users/msr/Documents/personal/GitHub/view-html-files-v2/public/books"


def format_time_delta(seconds):
    """Format time delta in seconds to a readable string"""
    return f"{seconds:.2f}s"


def get_all_chapters(book_id):
    """Get all chapters for a book"""
    start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}/chapters"
    print(f"API Request: GET {url}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        request_time = time.time() - start_time
        print(f"API Response: {response.status_code} (Time: {format_time_delta(request_time)})")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting chapters: {e}")
        return None


def get_chapter_content(book_id, chapter_id):
    """Get the content of a chapter"""
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        chapter_data = response.json()
        return chapter_data.get("content", "")
    except requests.exceptions.RequestException as e:
        print(f"Error getting chapter content: {e}")
        return ""


def update_chapter_content(book_id, chapter_id, content):
    """Update the content of a chapter in the database"""
    start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}"

    data = {"content": content}

    try:
        print(f"\nAPI Request: PUT {url} (updating chapter content)")
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        request_time = time.time() - start_time

        if response.status_code in [200, 201, 204]:
            print(
                f"API Response: {response.status_code} - Successfully updated chapter content in database (Time: {format_time_delta(request_time)})"
            )
            return True
        else:
            print(
                f"API Error: {response.status_code} - Failed to update chapter content (Time: {format_time_delta(request_time)})"
            )
            print(response.text)
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error updating chapter content: {e}")
        return False


def get_chapter_scenes(book_id, chapter_id):
    """Get existing scenes for a chapter"""
    start_time = time.time()
    url = f"{API_BASE_URL}/scenes?chapter_id={chapter_id}"
    print(f"API Request: GET {url}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        request_time = time.time() - start_time
        scenes = response.json()
        print(f"API Response: {response.status_code} (Time: {format_time_delta(request_time)})")
        return scenes
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        print(f"Error getting scenes for chapter: {e}")
        return []


def create_scenes_for_chapter(book_id, chapter_id, chapter_number):
    # Check if scenes already exist for this chapter
    existing_scenes = get_chapter_scenes(book_id, chapter_id)
    if existing_scenes and len(existing_scenes) > 0:
        print(f"Scenes already exist for Chapter {chapter_number} (ID: {chapter_id}).")
        return True

    prompt_start_time = time.time()
    custom_prompt = SCENE_GENERATION_PROMPT  # Use custom prompt if provided

    prompt_prep_time = time.time() - prompt_start_time
    print(f"Prepared prompt in {format_time_delta(prompt_prep_time)}")

    # Make the API request
    api_start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}/generate-scenes"
    data = {"user_prompt": custom_prompt}
    print(f"API Request: POST {url}")

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        api_time = time.time() - api_start_time

        print(f"API Response: {response.status_code} (Time: {format_time_delta(api_time)})")
        print(f"Successfully created scenes for chapter {chapter_number}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        print(f"Error creating scenes for chapter {chapter_number}: {e}")
        return False


def rewrite_chapter(book_id, chapter_id, chapter_number, chapter_title, original_content):
    """Rewrite a chapter using the streaming API endpoint"""
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}/rewrite"
    chunk_count = 0

    try:
        # Make request with stream=True to handle SSE
        print(f"API Request: POST {url} (streaming)")
        start_time = time.time()
        response = requests.post(url, headers=headers, stream=True)
        connection_time = time.time() - start_time
        print(f"Connection established in {format_time_delta(connection_time)}")

        if response.status_code == 200:
            print(f"API Response: {response.status_code} - Stream started")
            full_content = ""
            print(f"Receiving streamed rewrite for chapter {chapter_number}...")

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
                                content = data["content"]
                                full_content += content

                                # Update progress with spinning animation
                                chunk_count += 1
                                spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                                spinner_idx = chunk_count % len(spinner_chars)

                                # Every 25 chunks, update the counter with more details
                                if chunk_count % 25 == 0:
                                    progress_msg = f"\rRewriting chapter: {spinner_chars[spinner_idx]} {chunk_count} chunks | {len(full_content)} chars"
                                else:
                                    progress_msg = (
                                        f"\rRewriting chapter: {spinner_chars[spinner_idx]}"
                                    )

                                sys.stdout.write(progress_msg)
                                sys.stdout.flush()

                            # Handle any errors
                            if "error" in data:
                                print(f"\nError during rewriting: {data['error']}")
                                return None

                        except json.JSONDecodeError:
                            print(f"\nError parsing SSE data: {data_str}")

            print(f"\n\n{'-' * 60}")
            print(f"Chapter {chapter_number} rewrite complete! ({len(full_content)} characters)")
            print(f"{'-' * 60}\n")

            # Save the original and rewritten content to a file in book-specific subfolder
            book_save_dir = os.path.join(BASE_SAVE_DIR, f"book_{book_id}")
            os.makedirs(book_save_dir, exist_ok=True)

            # Format the filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in chapter_title if c.isalnum() or c in ". -_").replace(
                " ", "_"
            )
            filename = f"chapter_{chapter_number:02d}_{safe_title}_{timestamp}.html"
            file_path = os.path.join(book_save_dir, filename)

            # Create HTML content with styling
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chapter {chapter_number}: {chapter_title}</title>
    <style>
        body {{  
            font-family: 'Georgia', serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
            background-color: #f9f9f9;
            color: #333;
        }}
        h1, h2 {{  
            text-align: center;
            border-bottom: 2px solid #ddd;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        .content {{  
            background-color: white;
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            white-space: pre-wrap;
        }}
        .divider {{  
            text-align: center;
            margin: 40px 0;
            color: #888;
        }}
        .timestamp {{  
            text-align: right;
            font-size: 0.8em;
            color: #888;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>Chapter {chapter_number}: {chapter_title}</h1>
    
    <h2>Original Version</h2>
    <div class="content">
{original_content}
    </div>
    
    <div class="divider">* * * * *</div>
    
    <h2>Rewritten Version</h2>
    <div class="content">
{full_content}
    </div>
    
    <div class="timestamp">Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
</body>
</html>
            """

            # Write HTML content to file
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(html_content)

            print(f"Saved original and rewritten chapter to: {file_path}")

            # Update content in database if configured
            if UPDATE_DATABASE:
                if update_chapter_content(book_id, chapter_id, full_content):
                    print(
                        f"Chapter {chapter_number} content updated in database with rewritten version."
                    )
                else:
                    print(f"Failed to update Chapter {chapter_number} content in database.")

            return full_content
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error rewriting chapter: {e}")
        return None


def generate_chapter_content(book_id, chapter_id, chapter_number):
    prompt_start_time = time.time()
    custom_prompt = CHAPTER_CONTENT_PROMPT  # Use custom prompt if provided

    prompt_prep_time = time.time() - prompt_start_time
    print(f"Prepared content prompt in {format_time_delta(prompt_prep_time)}")

    api_start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}/generate-content"
    data = {"user_prompt": custom_prompt}

    print(f"API Request: POST {url} (streaming)")
    # Use stream=True for SSE response
    try:
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()
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
                                    progress_msg = (
                                        f"\rGenerating content: {spinner_chars[spinner_idx]}"
                                    )

                                sys.stdout.write(progress_msg)
                                sys.stdout.flush()
                            elif "error" in data:
                                print(f"\nError in stream: {data['error']}")
                        except json.JSONDecodeError:
                            print(f"\nInvalid JSON in data: {data_str}")

            streaming_time = time.time() - streaming_start_time
            words_count = len(full_content.split())
            print(
                f"\n\nChapter content generated in {format_time_delta(streaming_time)} ({words_count} words)"
            )

            # Update the chapter content in the database
            if UPDATE_DATABASE:
                if update_chapter_content(book_id, chapter_id, full_content):
                    print(f"Chapter {chapter_number} content updated in database.")
                else:
                    print(f"Failed to update Chapter {chapter_number} content in database.")

            return full_content
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error generating chapter content: {e}")
        return None


def process_chapter(book_id, chapter):
    """Process a single chapter: generate content and then rewrite it"""
    chapter_id = chapter.get("id")
    chapter_number = chapter.get("chapter_no")
    chapter_title = chapter.get("title", "Untitled")

    print(f"\n{'=' * 80}")
    print(f"Processing Chapter {chapter_number}: {chapter_title} (ID: {chapter_id})")
    print(f"{'=' * 80}\n")

    # Step 1: Create scenes if they don't exist
    if CREATE_SCENES:
        if not create_scenes_for_chapter(book_id, chapter_id, chapter_number):
            print(f"Failed to create scenes for Chapter {chapter_number}. Skipping.")
            return False

    # Step 2: Generate chapter content
    print(f"\n{'*' * 60}")
    print(f"Generating content for Chapter {chapter_number}: {chapter_title}")
    print(f"{'*' * 60}\n")

    original_content = generate_chapter_content(book_id, chapter_id, chapter_number)
    if not original_content:
        print(f"Failed to generate content for Chapter {chapter_number}. Skipping rewrite.")
        return False

    # Step 3: Rewrite the chapter (if enabled)
    if ENABLE_REWRITE:
        print(f"\n{'*' * 60}")
        print(f"Rewriting Chapter {chapter_number}: {chapter_title}")
        print(f"{'*' * 60}\n")

        rewritten_content = rewrite_chapter(
            book_id, chapter_id, chapter_number, chapter_title, original_content
        )
        if not rewritten_content:
            print(f"Failed to rewrite Chapter {chapter_number}.")
            return False

    return True


def process_chapters(book_id, chapter_numbers=None):
    """Process multiple chapters: generate content and rewrite them"""
    # Create base save directory and book-specific directory if they don't exist
    os.makedirs(BASE_SAVE_DIR, exist_ok=True)
    book_save_dir = os.path.join(BASE_SAVE_DIR, f"book_{book_id}")
    os.makedirs(book_save_dir, exist_ok=True)

    # Get all chapters
    all_chapters = get_all_chapters(book_id)
    if not all_chapters:
        print("Failed to retrieve chapters. Exiting.")
        return

    # Sort chapters by number
    all_chapters.sort(key=lambda x: x.get("chapter_no", 0))

    # Filter chapters to process
    chapters_to_process = []
    if chapter_numbers:
        # Process only specified chapters
        for chapter in all_chapters:
            if chapter.get("chapter_no") in chapter_numbers:
                chapters_to_process.append(chapter)
    else:
        # Process all chapters
        chapters_to_process = all_chapters

    if not chapters_to_process:
        print("No chapters to process. Exiting.")
        return

    # Display chapters to process
    print(f"\nFound {len(chapters_to_process)} chapters to process:")
    for chapter in chapters_to_process:
        print(
            f"  - Chapter {chapter.get('chapter_no', 'Unknown')}: {chapter.get('title', 'Untitled')} (ID: {chapter.get('id', 'Unknown')})"
        )

    # Process each chapter
    start_time = time.time()
    successful = 0
    for chapter in chapters_to_process:
        chapter_start_time = time.time()
        if process_chapter(book_id, chapter):
            chapter_time = time.time() - chapter_start_time
            print(
                f"Successfully processed Chapter {chapter.get('chapter_no', 'Unknown')} in {format_time_delta(chapter_time)}"
            )
            successful += 1
        else:
            print(f"Failed to process Chapter {chapter.get('chapter_no', 'Unknown')}")

    # Print summary
    total_time = time.time() - start_time
    print(f"\n{'=' * 80}")
    print(f"Processing complete!")
    print(f"Successfully processed {successful} out of {len(chapters_to_process)} chapters")
    print(f"Total time: {format_time_delta(total_time)}")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    # Parse command line arguments if provided
    if len(sys.argv) > 1:
        try:
            # Convert command line arguments to integers
            chapter_numbers = [int(arg) for arg in sys.argv[1:]]
            print(f"Processing chapters from command line: {chapter_numbers}")
            process_chapters(BOOK_ID, chapter_numbers)
        except ValueError:
            print("Error: Chapter numbers must be integers.")
            sys.exit(1)
    else:
        # Use the hardcoded chapter numbers
        print(f"Processing hardcoded chapters: {CHAPTERS_TO_PROCESS}")
        process_chapters(BOOK_ID, CHAPTERS_TO_PROCESS)
