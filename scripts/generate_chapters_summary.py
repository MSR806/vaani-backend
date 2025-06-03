import requests
import time
import sys
from typing import List

# API Base URL - assuming local development
API_BASE_URL = "http://localhost/vaani/api/v1"  # Update as needed

# Access token placeholder - User will update this
ACCESS_TOKEN = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ill3OGhmeWV2cjJneG9qY3oxMWIzeCJ9.eyJpc3MiOiJodHRwczovL2Rldi02bTN2N3RnaXZ1enJzNXdlLnVzLmF1dGgwLmNvbS8iLCJzdWIiOiJnb29nbGUtb2F1dGgyfDEwOTUwNjExNTIyMjY5ODE2MjY2NCIsImF1ZCI6WyI5YTI0NDkyZi04MDNjLTQ2MWMtYjA1MS1mMWRkN2NlM2M1MDQiLCJodHRwczovL2Rldi02bTN2N3RnaXZ1enJzNXdlLnVzLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NDg4Mzk1MDAsImV4cCI6MTc0ODkyNTkwMCwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkhXWFlNRHVsYXFxY3UzTTJmRHduZlJpU0NDUzRNUFN2IiwicGVybWlzc2lvbnMiOlsiYm9vazpkZWxldGUiLCJib29rOnJlYWQiLCJib29rOndyaXRlIiwic3RvcnlfYm9hcmQ6cmVhZCIsInN0b3J5X2JvYXJkOndyaXRlIiwidGVtcGxhdGU6cmVhZCIsInRlbXBsYXRlOndyaXRlIl19.DYmOSr6Ps2H0Dg_iM3nGoKPMtWvkrYxHh_TwW9Abv-DgxdRmw-avGYqRZpivkI-FZy-yi-5axBnXMY5S9SVraigIfb6gBsZb3qvfkVKok_-PqsyMXB06a4-61EZyuy923xZTEhq64-oZsJWAyXXE7GyAiB7eie__n4MbqkN8P7BMfGMxI8F-wny6QfOcVHIw5bTxZZP24HHbBGKE6lJQ9YAgCS5JV-x5Neqx3I9FcQIETEHY8i0pwQ5ZCvFHhCJ4w_h_G7gd1hqmBJVPCZ3akm-FtNBU7F-KMR_0TDwD3iZgBvH2sDxLh7DFjZ4gehLz6WUiestrK_zmAs1XIs-LvA"

# Configuration
STORYBOARD_ID = 42  # Update this with your storyboard ID
START_PLOT_BEAT = 886  # Update this with your starting plot beat ID
END_PLOT_BEAT = 905    # Update this with your ending plot beat ID

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