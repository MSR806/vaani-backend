import requests
import json
import time
import os
import sys
import argparse
import re
import datetime
from keys import ACCESS_TOKEN

# Try to import BeautifulSoup, but provide fallback if not available
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    print("BeautifulSoup not found. Using regex-based HTML cleaning.")

# API Base URL - assuming local development
API_BASE_URL = "http://localhost/vaani/api/v1"  # Update as needed

# Headers for API requests
headers = {
    "Authorization": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def clean_html_content(html_content):
    if not html_content:
        return ""
    
    if BEAUTIFULSOUP_AVAILABLE:
        # Parse HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get text content and preserve paragraph structure
        paragraphs = soup.find_all('p')
        if paragraphs:
            # If we have paragraphs, preserve their structure
            cleaned_text = "\n\n".join(p.get_text() for p in paragraphs)
        else:
            # Otherwise just get all text
            cleaned_text = soup.get_text()
    else:
        # Fallback method using regex
        # Remove HTML tags
        cleaned_text = re.sub(r'<[^>]+>', '\n', html_content)
        
        # Remove style attributes
        cleaned_text = re.sub(r'style=\"[^\"]*\"', '', cleaned_text)
    
    # Clean up extra whitespace for both methods
    cleaned_text = "\n".join(line.strip() for line in cleaned_text.splitlines() if line.strip())
    
    return cleaned_text

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

def create_output_directory(book_id, book_title):
    # Create directory path using the specified absolute path
    base_dir = "/Users/msr/Documents/personal/GitHub/view-html-files-v2/books"
    dir_path = os.path.join(base_dir, f"{book_title} ({book_id})")
    
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
        combined_file_path = os.path.join(output_dir, f"{book_title}.html")
        all_chapters_file = open(combined_file_path, 'w', encoding='utf-8')
        all_chapters_file.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{book_title}</title>
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
        .chapter-divider {{  
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
    <h1>{book_title}</h1>
""")
    
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
        if output_format != "single" and output_format != "docs":
            # Format the filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in chapter_title if c.isalnum() or c in ". -_").replace(" ", "_")
            filename = f"chapter_{chapter_no:02d}_{safe_title}_{timestamp}.html"
            file_path = os.path.join(output_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write HTML structure with improved formatting
                f.write(f"""<!DOCTYPE html>
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
        .timestamp {{  
            text-align: right;
            font-size: 0.8em;
            color: #888;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>Chapter {chapter_no}: {chapter_title}</h1>
    
    <div class="content">
{content}
    </div>
    
    <div class="timestamp">Downloaded on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
</body>
</html>""")
            
            print(f"Saved Chapter {chapter_no} content to {file_path}")

        
        # Append to combined file if using single file format
        if output_format == "single" and all_chapters_file:
            all_chapters_file.write(f"""
    <h2>Chapter {chapter_no}: {chapter_title}</h2>
    <div class="content">
{content}
    </div>
    <div class="chapter-divider">* * * * *</div>
""")
        
        successful_downloads += 1
    
    # Close the combined file if it was created
    if output_format == "single" and all_chapters_file:
        all_chapters_file.write(f"""
    <div class="timestamp">Downloaded on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
</body>
</html>""")
        all_chapters_file.close()
        print(f"\nAll chapters saved to combined file: {combined_file_path}")
    
    # Create a single docs file for the entire book if using docs format
    if output_format == "docs":
        combined_docs_path = os.path.join(output_dir, f"{book_title}.txt")
        with open(combined_docs_path, 'w', encoding='utf-8') as f:
            f.write(f"{book_title}\n\n")
            
            # Instead of fetching chapters again, use the ones we already processed
            for i, chapter in enumerate(chapters):
                chapter_no = chapter.get("chapter_no")
                chapter_title = chapter.get("title", "Untitled")
                chapter_id = chapter.get("id")
                
                # Get chapter content if we haven't already
                chapter_details = get_chapter_content(book_id, chapter_id)
                if chapter_details:
                    content = chapter_details.get("content", "").strip()
                    if content:
                        # Clean HTML tags from content
                        clean_content = clean_html_content(content)
                        
                        f.write(f"\n\nChapter {chapter_no}: {chapter_title}\n\n")
                        f.write(clean_content)
                        successful_downloads += 1
                        print(f"Added Chapter {chapter_no} to combined file")
            
        print(f"\nAll chapters saved to combined docs file: {combined_docs_path}")
    
    total_time = time.time() - total_start_time
    print(f"\nDownload complete! Downloaded {successful_downloads} out of {len(chapters)} chapters")
    print(f"Total time: {format_time_delta(total_time)}")
    print(f"Files saved to: {output_dir}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Download all chapters for a book")
    parser.add_argument("book_id", help="ID of the book to download chapters for")
    parser.add_argument("--format", choices=["text", "single", "docs"], default="text",
                        help="Output format: 'text' for individual HTML files, 'single' for one combined HTML file, 'docs' for one combined text file for Google Docs")
    
    args = parser.parse_args()
    
    # Create the output base directory if it doesn't exist
    if not os.path.exists("output"):
        os.makedirs("output")
    
    # Download book chapters
    download_book_chapters(args.book_id, args.format)

if __name__ == "__main__":
    main()
