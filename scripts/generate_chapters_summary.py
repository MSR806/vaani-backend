import sys
import time
from typing import List

import requests
from keys import ACCESS_TOKEN

# API Base URL - assuming local development
API_BASE_URL = "http://localhost/vaani/api/v1"  # Update as needed

# Configuration
STORYBOARD_ID = 67  # Update this with your storyboard ID
START_PLOT_BEAT = 2145  # Update this with your starting plot beat ID
END_PLOT_BEAT = 2164  # Update this with your ending plot beat ID

# Headers for API requests
headers = {"Authorization": ACCESS_TOKEN, "Content-Type": "application/json"}


def format_time_delta(seconds: float) -> str:
    """Format time delta in a human-readable format."""
    return f"{seconds:.2f}s"


def generate_chapters_summary(storyboard_id: int, plot_beat_id: int) -> bool:
    """Generate chapters summary for a specific plot beat."""
    start_time = time.time()
    url = f"{API_BASE_URL}/storyboard/{storyboard_id}/generate-chapters-summary"
    data = {"plot_beat_id": plot_beat_id}

    print(f"Generating chapters summary for plot beat {plot_beat_id}...")
    response = requests.post(url, headers=headers, json=data)
    request_time = time.time() - start_time

    if response.status_code == 200:
        result = response.json()
        print(
            f"Successfully generated chapters summary for plot beat {plot_beat_id} (Time: {format_time_delta(request_time)})"
        )
        print(f"Message: {result.get('message', 'No message')}")
        return True
    else:
        print(
            f"Error generating chapters summary for plot beat {plot_beat_id} (Time: {format_time_delta(request_time)})"
        )
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
