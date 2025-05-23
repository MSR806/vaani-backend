import requests
import time
import sys
from typing import List

# API Base URL - assuming local development
API_BASE_URL = "http://localhost/vaani/api/v1"  # Update as needed

# Access token placeholder - User will update this
ACCESS_TOKEN = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Il9QbzVTVHpUWEZXOHdMa1FseTlUMSJ9.eyJpc3MiOiJodHRwczovL3ZhYW5pLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJnb29nbGUtb2F1dGgyfDEwOTUwNjExNTIyMjY5ODE2MjY2NCIsImF1ZCI6WyJjZjQ4MWQ0NC1mY2RiLTRlOWMtYTI5ZC00ZDk0OWQ0MTliY2EiLCJodHRwczovL3ZhYW5pLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NDgyNDgzODYsImV4cCI6MTc0ODMzNDc4Niwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNCVnNDWmg5ZHN3U24wUXJqVlFUMGlDdUVDbXlScTg0IiwicGVybWlzc2lvbnMiOlsiYm9vazpkZWxldGUiLCJib29rOnJlYWQiLCJib29rOndyaXRlIl19.ftzsYDLwfgKUE4EfBhcOPhQqNRQvQpJz4Euru9yvF-9xrY5RAl6NfS13hxiJDmsynhqWHHolWbkvu6Igycu3BM6Zdz0P6NcHUK3rFhLLDpRErsoHTSgC-pviOT2wV-09rYuN_yeejhdMA0Kzq1lVgud3Ch5FIZ4oAmcJJO_B3dhVP4uCtaoSsNbAcyPsWHNGdA9LR-3IlQWznvghdiNXBzXL-JBbUSzZlzbis4UcdiKPeOi2Zq5rUwCZQ3PYG5IrbbjtlaBfnFNvG9ZzYKUv6hEBDT0HR0bDAiK-pwg2AkquGZmWku-0L1Ep9g11WNVX5HdlhxrizNGw0GUpIBtz5A"

# Configuration
STORYBOARD_ID = 12  # Update this with your storyboard ID
START_PLOT_BEAT = 1791  # Update this with your starting plot beat ID
END_PLOT_BEAT = 1830    # Update this with your ending plot beat ID

# Headers for API requests
headers = {
    "Authorization": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def format_time_delta(seconds: float) -> str:
    """Format time delta in a human-readable format."""
    return f"{seconds:.2f}s"

def generate_chapters_summary(storyboard_id: int, plot_beat_id: int) -> bool:
    """Generate chapters summary for a specific plot beat."""
    start_time = time.time()
    url = f"{API_BASE_URL}/storyboard/{storyboard_id}/generate-chapters-summary"
    data = {
        "plot_beat_id": plot_beat_id
    }
    
    print(f"Generating chapters summary for plot beat {plot_beat_id}...")
    response = requests.post(url, headers=headers, json=data)
    request_time = time.time() - start_time
    
    if response.status_code == 200:
        result = response.json()
        print(f"Successfully generated chapters summary for plot beat {plot_beat_id} (Time: {format_time_delta(request_time)})")
        print(f"Message: {result.get('message', 'No message')}")
        return True
    else:
        print(f"Error generating chapters summary for plot beat {plot_beat_id} (Time: {format_time_delta(request_time)})")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def main():
    if START_PLOT_BEAT > END_PLOT_BEAT:
        print("Error: START_PLOT_BEAT must be less than or equal to END_PLOT_BEAT")
        sys.exit(1)
    
    total_start_time = time.time()
    successful = 0
    failed = 0
    
    for plot_beat_id in range(START_PLOT_BEAT, END_PLOT_BEAT + 1):
        if generate_chapters_summary(STORYBOARD_ID, plot_beat_id):
            successful += 1
        else:
            failed += 1
    
    total_time = time.time() - total_start_time
    print("\nSummary:")
    print(f"Total time: {format_time_delta(total_time)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total plot beats processed: {successful + failed}")

if __name__ == "__main__":
    main() 