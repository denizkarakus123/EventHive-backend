from usernames import USERNAMES
import scrape_profile


SF_API_KEY = "kMgCKYBeGrNKdE30wHTZfjtZQtwEn9qVNbyeTQTZClRQDc7Q2Z2XFZWhcpS4b5yDZg4PyIoJsNl3W0AFHx"
userstoparse = USERNAMES[:10]

for username in userstoparse:
    start_date = "2024-11-01"  # Start scraping posts from this date onwards
    scrape_profile.scrape_ig_profile(username=username, sf_api_key=SF_API_KEY, start_date=start_date)