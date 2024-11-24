import sys
from usernames import USERNAMES
import scrape_profile

SF_API_KEY = "kMgCKYBeGrNKdE30wHTZfjtZQtwEn9qVNbyeTQTZClRQDc7Q2Z2XFZWhcpS4b5yDZg4PyIoJsNl3W0AFHx"

def main():
    start_date = "2024-11-01"
    scrape_profile.scrape_ig_profile('hackstreet_boys_mcgill', sf_api_key=SF_API_KEY, start_date=start_date)
    scrape_profile.move_json_file('test_post_data/hackstreet_boys_mcgill_posts.json', 'test_post_data/json_files')

if __name__ == "__main__":
    main()
