import sys
from usernames import USERNAMES
import scrape_profile

SF_API_KEY = "kMgCKYBeGrNKdE30wHTZfjtZQtwEn9qVNbyeTQTZClRQDc7Q2Z2XFZWhcpS4b5yDZg4PyIoJsNl3W0AFHx"

def main():
    # Ensure the script is called with the required arguments
    if len(sys.argv) != 3:
        print("Usage: python scrape_profiles.py <start:int> <end:int>")
        sys.exit(1)

    # Parse command-line arguments
    try:
        start = int(sys.argv[1])
        end = int(sys.argv[2])
    except ValueError:
        print("Both start and end must be integers.")
        sys.exit(1)

    # Ensure valid range
    if start < 0 or end <= start or end > len(USERNAMES):
        print(f"Invalid range. Ensure 0 <= start < end <= {len(USERNAMES)}")
        sys.exit(1)

    # Slice the usernames list based on the provided range
    userstoparse = USERNAMES[start:end]
    print(f"Scraping profiles for usernames {userstoparse}...")

    # Scrape profiles
    for username in userstoparse:
        start_date = "2024-11-01"  # Start scraping posts from this date onwards
        scrape_profile.scrape_ig_profile(username=username, sf_api_key=SF_API_KEY, start_date=start_date)

if __name__ == "__main__":
    main()
