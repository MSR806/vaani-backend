import requests
import json
import time
import os
import sys
import argparse

# API Base URL - assuming local development
API_BASE_URL = "http://localhost/vaani/api/v1"  # Update as needed

# Access token placeholder - User will update this
ACCESS_TOKEN = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Il9QbzVTVHpUWEZXOHdMa1FseTlUMSJ9.eyJpc3MiOiJodHRwczovL3ZhYW5pLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJnb29nbGUtb2F1dGgyfDEwOTUwNjExNTIyMjY5ODE2MjY2NCIsImF1ZCI6WyJjZjQ4MWQ0NC1mY2RiLTRlOWMtYTI5ZC00ZDk0OWQ0MTliY2EiLCJodHRwczovL3ZhYW5pLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NDg0MjY4NTYsImV4cCI6MTc0ODUxMzI1Niwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNCVnNDWmg5ZHN3U24wUXJqVlFUMGlDdUVDbXlScTg0IiwicGVybWlzc2lvbnMiOlsiYm9vazpkZWxldGUiLCJib29rOnJlYWQiLCJib29rOndyaXRlIl19.vno55nXeO-Y2MYw5a7R6D5LEnwxaYO4XrhQrPnFUgOXIQfN9vKl9V1COoygEQKe6heLazRH_cQlbsrm7UZoNl6gu5vFv93HDbVKDhZzN1OzHJ0-RPS4Ymj3Spdy3Br6ipJRcJAH_yPg1xiCITgOo_oo6eDTq75SvD8p_oBJkl4qJ_cVwgq_spxRyDYqjydodhEr_RCJyKfWPDRZatlyMIoCzJ8OL7_3h84jU0T5f_Nh3hOsm0sxjuwAjGnqaK3Of8Vc_-Kd44MH9kc8bMaQ9BfVEbiGabamGficmHC8rEbV6bd02YeLEH4EdUKxj8feNUbzegFR8zzmUvy7NenJN_Q"

# Headers for API requests
headers = {
    "Authorization": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def format_time_delta(seconds):
    # Format time deltas for better readability
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"

def get_book_details(book_id):
    start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}"
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

def get_chapter_content(book_id, chapter_id):
    start_time = time.time()
    url = f"{API_BASE_URL}/books/{book_id}/chapters/{chapter_id}"
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

def create_output_directory(book_id, book_title):
    # Create a clean directory name from the book title
    clean_title = ''.join(c if c.isalnum() or c == ' ' else '_' for c in book_title).strip()
    clean_title = clean_title.replace(' ', '_')
    
    # Create directory path
    dir_path = f"output/book_{book_id}_{clean_title}"
    
    # Create directory if it doesn't exist
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Created output directory: {dir_path}")
    else:
        print(f"Using existing output directory: {dir_path}")
    
    return dir_path

def download_book_chapters(book_id, output_format="text"):
    print(f"Starting download of all chapters for Book ID: {book_id}")
    total_start_time = time.time()
    
    # Get book details
    book = get_book_details(book_id)
    if not book:
        print(f"Unable to retrieve book with ID {book_id}")
        return False
    
    book_title = book.get("title", f"Book_{book_id}")
    print(f"Book Title: {book_title}")
    
    # Create output directory for this book
    output_dir = create_output_directory(book_id, book_title)
    
    # Get all chapters
    chapters = get_all_chapters(book_id)
    if not chapters:
        print(f"No chapters found for book ID {book_id}")
        return False
    
    print(f"Found {len(chapters)} chapters")
    
    # Create combined file for whole book
    all_chapters_file = None
    
    if output_format == "single":
        combined_file_path = os.path.join(output_dir, f"{book_title}_complete.txt")
        all_chapters_file = open(combined_file_path, 'w', encoding='utf-8')
        all_chapters_file.write(f"# {book_title}\n\n")
    
    # Download each chapter
    successful_downloads = 0
    
    for chapter in chapters:
        chapter_id = chapter.get("id")
        chapter_no = chapter.get("chapter_no")
        chapter_title = chapter.get("title", "Untitled")
        
        print(f"\nProcessing Chapter {chapter_no}: {chapter_title} (ID: {chapter_id})")
        
        # Get full chapter details with content
        chapter_details = get_chapter_content(book_id, chapter_id)
        if not chapter_details:
            print(f"Failed to retrieve content for Chapter {chapter_no}")
            continue
        
        # Get the content from chapter details
        content = chapter_details.get("content", "").strip()
        
        if not content:
            print(f"No content found for Chapter {chapter_no}")
            continue
        
        # Write to individual file
        if output_format != "single":
            # Create file name with chapter number for proper ordering
            file_name = f"chapter_{chapter_no:03d}_{chapter_title}.txt"
            clean_file_name = ''.join(c if c.isalnum() or c in ' _-.' else '_' for c in file_name)
            file_path = os.path.join(output_dir, clean_file_name)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write chapter header
                f.write(f"# Chapter {chapter_no}: {chapter_title}\n\n")
                f.write(content)
                
            # Also get scenes if needed
            scenes = get_chapter_scenes(book_id, chapter_id)
            if scenes and len(scenes) > 0:
                scenes_file_name = f"chapter_{chapter_no:03d}_{chapter_title}_scenes.json"
                clean_scenes_file_name = ''.join(c if c.isalnum() or c in ' _-.' else '_' for c in scenes_file_name)
                scenes_file_path = os.path.join(output_dir, clean_scenes_file_name)
                
                with open(scenes_file_path, 'w', encoding='utf-8') as f:
                    json.dump(scenes, f, indent=2)
                    
                print(f"Saved {len(scenes)} scenes for Chapter {chapter_no}")
            
            print(f"Saved Chapter {chapter_no} content to {file_path}")
        
        # Append to combined file if using single file format
        if output_format == "single" and all_chapters_file:
            all_chapters_file.write(f"## Chapter {chapter_no}: {chapter_title}\n\n")
            all_chapters_file.write(content)
            all_chapters_file.write("\n\n---\n\n")
        
        successful_downloads += 1
    
    # Close the combined file if it was created
    if output_format == "single" and all_chapters_file:
        all_chapters_file.close()
        print(f"\nAll chapters saved to combined file: {combined_file_path}")
    
    total_time = time.time() - total_start_time
    print(f"\nDownload complete! Downloaded {successful_downloads} out of {len(chapters)} chapters")
    print(f"Total time: {format_time_delta(total_time)}")
    print(f"Files saved to: {output_dir}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Download all chapters from a book")
    parser.add_argument("--book_id", type=int, required=True, help="ID of the book to download chapters from")
    parser.add_argument("--format", choices=["text", "single"], default="text", 
                       help="Output format: 'text' for individual files, 'single' for one combined file")
    
    args = parser.parse_args()
    
    # Create the output base directory if it doesn't exist
    if not os.path.exists("output"):
        os.makedirs("output")
    
    # Download book chapters
    download_book_chapters(args.book_id, args.format)

if __name__ == "__main__":
    main()
