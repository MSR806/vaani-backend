import requests
import json
import time
import sys
import datetime
import os

# API Base URL - assuming local development
API_BASE_URL = "http://localhost/vaani/api/v1"  # Update as needed

# Access token placeholder - User will update this
ACCESS_TOKEN = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ill3OGhmeWV2cjJneG9qY3oxMWIzeCJ9.eyJpc3MiOiJodHRwczovL2Rldi02bTN2N3RnaXZ1enJzNXdlLnVzLmF1dGgwLmNvbS8iLCJzdWIiOiJnb29nbGUtb2F1dGgyfDEwOTUwNjExNTIyMjY5ODE2MjY2NCIsImF1ZCI6WyI5YTI0NDkyZi04MDNjLTQ2MWMtYjA1MS1mMWRkN2NlM2M1MDQiLCJodHRwczovL2Rldi02bTN2N3RnaXZ1enJzNXdlLnVzLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NDg4Mzk1MDAsImV4cCI6MTc0ODkyNTkwMCwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkhXWFlNRHVsYXFxY3UzTTJmRHduZlJpU0NDUzRNUFN2IiwicGVybWlzc2lvbnMiOlsiYm9vazpkZWxldGUiLCJib29rOnJlYWQiLCJib29rOndyaXRlIiwic3RvcnlfYm9hcmQ6cmVhZCIsInN0b3J5X2JvYXJkOndyaXRlIiwidGVtcGxhdGU6cmVhZCIsInRlbXBsYXRlOndyaXRlIl19.DYmOSr6Ps2H0Dg_iM3nGoKPMtWvkrYxHh_TwW9Abv-DgxdRmw-avGYqRZpivkI-FZy-yi-5axBnXMY5S9SVraigIfb6gBsZb3qvfkVKok_-PqsyMXB06a4-61EZyuy923xZTEhq64-oZsJWAyXXE7GyAiB7eie__n4MbqkN8P7BMfGMxI8F-wny6QfOcVHIw5bTxZZP24HHbBGKE6lJQ9YAgCS5JV-x5Neqx3I9FcQIETEHY8i0pwQ5ZCvFHhCJ4w_h_G7gd1hqmBJVPCZ3akm-FtNBU7F-KMR_0TDwD3iZgBvH2sDxLh7DFjZ4gehLz6WUiestrK_zmAs1XIs-LvA"

# Headers for API requests
headers = {
    "Authorization": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

# Hardcoded book ID - update as needed
BOOK_ID = 49

# Chapters to rewrite - update as needed
CHAPTERS_TO_REWRITE = [1]  # Example: rewrite chapter 1


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


def rewrite_chapter(book_id, chapter_id):
    """Rewrite a chapter using the streaming API endpoint"""
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}/rewrite"
    
    try:
        # Make request with stream=True to handle SSE
        print(f"API Request: GET {url} (streaming)")
        response = requests.get(url, headers=headers, stream=True)
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
                    line = line.decode('utf-8')
                    # SSE format begins with 'data: '
                    if line.startswith('data:'):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            print("\nStream completed.")
                            break
                        
                        try:
                            # Parse the JSON data
                            data = json.loads(data_str)
                            if 'content' in data:
                                content = data['content']
                                print(content, end="", flush=True)
                                full_content += content
                                
                            # Handle any errors
                            if "error" in data:
                                print(f"\nError during rewriting: {data['error']}")
                                return None
                                
                        except json.JSONDecodeError:
                            print(f"\nError parsing SSE data: {data_str}")
            
            print(f"\n{'-' * 60}")
            print(f"Chapter {chapter_id} rewrite complete!")
            print(f"{'-' * 60}\n")
            
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
        
        # Confirm before proceeding
        confirmation = input(f"Rewrite Chapter {chapter_no}? (y/n): ")
        if confirmation.lower() != 'y':
            print(f"Skipping Chapter {chapter_no}.")
            continue
        
        # Start the rewrite process
        start_time = time.time()
        rewritten_content = rewrite_chapter(BOOK_ID, chapter_id)
        end_time = time.time()
        
        if rewritten_content:
            duration = end_time - start_time
            print(f"Chapter {chapter_no} rewritten in {duration:.2f} seconds.")
        else:
            print(f"Failed to rewrite Chapter {chapter_no}.")
    
    print("\nChapter rewrite process complete!")


if __name__ == "__main__":
    main()
