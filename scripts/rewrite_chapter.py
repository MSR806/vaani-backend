import datetime
import html
import json
import os
import sys
import time

import requests

# API Base URL - assuming local development
API_BASE_URL = "http://localhost/vaani/api/v1"  # Update as needed

# Access token placeholder - User will update this
ACCESS_TOKEN = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ill3OGhmeWV2cjJneG9qY3oxMWIzeCJ9.eyJpc3MiOiJodHRwczovL2Rldi02bTN2N3RnaXZ1enJzNXdlLnVzLmF1dGgwLmNvbS8iLCJzdWIiOiJnb29nbGUtb2F1dGgyfDEwOTUwNjExNTIyMjY5ODE2MjY2NCIsImF1ZCI6WyI5YTI0NDkyZi04MDNjLTQ2MWMtYjA1MS1mMWRkN2NlM2M1MDQiLCJodHRwczovL2Rldi02bTN2N3RnaXZ1enJzNXdlLnVzLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NDg5NDkwNjAsImV4cCI6MTc0OTAzNTQ2MCwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkhXWFlNRHVsYXFxY3UzTTJmRHduZlJpU0NDUzRNUFN2IiwicGVybWlzc2lvbnMiOlsiYm9vazpkZWxldGUiLCJib29rOnJlYWQiLCJib29rOndyaXRlIiwic3RvcnlfYm9hcmQ6cmVhZCIsInN0b3J5X2JvYXJkOndyaXRlIiwidGVtcGxhdGU6cmVhZCIsInRlbXBsYXRlOndyaXRlIl19.NEZIBi7CP5weOYTBaug2cJttosrqA6o8cPAfmpMdoEhAmuWlcQhh5T6fd4ATshPbEXBKVyOzlsLiEeYLhwDBqvGJMwt9mDPY-vy9ySO2Xp6MwJ3or_s2GNEEVawyw2iDxqjVD4Sb-zY27i_D35wyGdkSJ8oMXGSlkvhUhLubUnKmt6cKVM2_-8qEBHmGZlASVBUPAMwJl2s36Ir-e-vsp8oFxwJDtQCfwYMPm2K9L19yHId0Kr3I_wIKyHeYqDBy6EUo3h0Jr9ByG5Lvtv-3u7QmmOJYtC0Iak6jiitmtrt4GqCBuDDkVbRCl7rnLbYIPzCp2yLci_fKqZCLLwR6Bw"

# Headers for API requests
headers = {"Authorization": ACCESS_TOKEN, "Content-Type": "application/json"}

# Hardcoded book ID - update as needed
BOOK_ID = 49

# Chapters to rewrite - update as needed
# CHAPTERS_TO_REWRITE = [x for x in range(10, 20 +1)]
CHAPTERS_TO_REWRITE = [17]

# Whether to update the chapter content in the database
UPDATE_DATABASE = False


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


def format_time_delta(seconds):
    """Format time delta in seconds to a readable string"""
    return f"{seconds:.2f}s"


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


def rewrite_chapter(book_id, chapter_id, chapter_no, chapter_title, original_content):
    """Rewrite a chapter using the streaming API endpoint"""
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}/rewrite"
    chunk_count = 0

    try:
        # Make request with stream=True to handle SSE
        print(f"API Request: GET {url} (streaming)")
        response = requests.post(url, headers=headers, stream=True)
        response.raise_for_status()

        # Create a buffer to hold the complete rewritten content
        full_content = ""

        print(f"\n{'-' * 60}")
        print(f"Rewriting Chapter {chapter_id}...")
        print(f"{'-' * 60}")

        if response.status_code == 200:
            print(f"API Response: {response.status_code} - Stream started")
            print(f"Receiving streamed content...")

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
            print(f"Chapter {chapter_no} rewrite complete! ({len(full_content)} characters)")
            print(f"{'-' * 60}\n")

            # Save the original and rewritten content to a file
            save_dir = os.path.join(os.getcwd(), "rewritten_chapters")
            os.makedirs(save_dir, exist_ok=True)

            # Format the filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in chapter_title if c.isalnum() or c in ". -_").replace(
                " ", "_"
            )
            filename = f"chapter_{chapter_no:02d}_{safe_title}_{timestamp}.html"
            file_path = os.path.join(save_dir, filename)

            # Create HTML content with styling
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chapter {chapter_no}: {chapter_title}</title>
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
    <h1>Chapter {chapter_no}: {html.escape(chapter_title)}</h1>
    
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
                    print(f"Chapter {chapter_no} content updated in database.")
                else:
                    print(f"Failed to update Chapter {chapter_no} content in database.")

            return full_content
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error rewriting chapter: {e}")
        return None


def main():
    print("\n========================================")
    print("  Chapter Rewrite Script")
    print("========================================\n")

    # Start timer
    start_time = time.time()
    print(f"Started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Get all chapters for the book
    print(f"Getting all chapters for book {BOOK_ID}...")
    chapters = get_all_chapters(BOOK_ID)

    if not chapters:
        print("No chapters found or error retrieving chapters.")
        return

    # Sort chapters by chapter number
    chapters.sort(key=lambda x: x.get("chapter_no", 0))

    # Filter chapters to rewrite
    if len(sys.argv) > 1:
        # Use chapter numbers from command line args
        chapter_numbers_to_rewrite = [int(arg) for arg in sys.argv[1:]]
    else:
        # Use predefined list
        chapter_numbers_to_rewrite = CHAPTERS_TO_REWRITE

    print(f"Book ID: {BOOK_ID}")
    print(f"Chapter numbers to rewrite: {chapter_numbers_to_rewrite}")
    print("\nStarting chapter rewrites...\n")

    # Process each chapter
    for chapter in chapters:
        chapter_id = chapter.get("id")
        chapter_no = chapter.get("chapter_no")
        chapter_title = chapter.get("title", "Untitled")

        # Skip chapters not in our list
        if chapter_no not in chapter_numbers_to_rewrite:
            continue

        print(f"Found Chapter {chapter_no}: '{chapter_title}' (ID: {chapter_id})")
        print(f"Rewriting Chapter {chapter_no}...")

        # Get the original chapter content
        print(f"Fetching original content for Chapter {chapter_no}...")
        original_content = get_chapter_content(BOOK_ID, chapter_id)
        if not original_content:
            print(f"Failed to retrieve original content for Chapter {chapter_no}. Skipping.")
            continue

        print(f"Original content: {len(original_content)} characters")
        print(f"Starting rewrite process...")

        # Start the rewrite process
        start_time = time.time()
        rewritten_content = rewrite_chapter(
            BOOK_ID, chapter_id, chapter_no, chapter_title, original_content
        )
        end_time = time.time()

        if rewritten_content:
            duration = end_time - start_time
            print(f"Chapter {chapter_no} rewritten in {duration:.2f} seconds.")
        else:
            print(f"Failed to rewrite Chapter {chapter_no}.")

    print("\nChapter rewrite process complete!")


if __name__ == "__main__":
    main()
