import time
import json
from usernames import USERNAMES
import scrape_profile
import instaPostToEvent

SF_API_KEY = "kMgCKYBeGrNKdE30wHTZfjtZQtwEn9qVNbyeTQTZClRQDc7Q2Z2XFZWhcpS4b5yDZg4PyIoJsNl3W0AFHx"
POLL_INTERVAL = 10  # Time in seconds between polls

def poll_instagram(username: str, sf_api_key: str, start_datetime: str):
    """
    Continuously polls Instagram for new posts for the given username and updates the database.
    
    Args:
        username (str): Instagram username to poll.
        sf_api_key (str): ScrapeFish API key.
        start_datetime (str): Start datetime for scraping (format: YYYY-MM-DD HH:MM:SS).
    """
    print(f"Starting continuous polling for {username} starting from {start_datetime}...")

    while True:
        try:
            # Scrape the profile for new posts
            new_posts = scrape_profile.scrape_ig_profile(username, sf_api_key=sf_api_key, start_datetime=start_datetime)

            # Check if new posts were found
            if new_posts:
                print(f"{len(new_posts)} new post(s) detected for {username}. Processing...")
                
                # Move JSON file to `json_files` directory
                scrape_profile.move_json_file(f"test_post_data/{username}_posts.json", "test_post_data/json_files")

                # Run the instaPostToEvent logic
                json_file_path = f"test_post_data/json_files/{username}_posts.json"
                with open(json_file_path, 'r') as json_file:
                    data = json.load(json_file)

                for item in data:
                    caption = item['description']
                    image_description = item.get('image_description', "")
                    event_data = instaPostToEvent.extract_event_data(caption, image_description)
                    if event_data:
                        instaPostToEvent.save_event_to_db(event_data)

                print(f"Processed and saved events from new posts for {username}.")
            else:
                print(f"No new posts detected for {username}.")
        
        except Exception as e:
            print(f"Error during polling for {username}: {e}")

        # Wait for the next polling interval
        print(f"Waiting {POLL_INTERVAL} seconds before checking again...")
        time.sleep(POLL_INTERVAL)


def main():
    # Define the start datetime (format: YYYY-MM-DD HH:MM:SS)
    start_datetime = "2024-11-20 01:51:00"  # Replace with your desired start datetime
    username = "hackstreet_boys_mcgill"  # Replace with your desired Instagram username

    # Start the polling process
    try:
        poll_instagram(username, SF_API_KEY, start_datetime)
    except KeyboardInterrupt:
        print("Polling stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
