from typing import Dict, Union, Optional, Any, List
import json
import requests
import pandas as pd
import datetime
import os
import shutil


def validate_username(username: str, sf_api_key: str) -> Optional[str]:
    """
    Validates if the given username is valid and not private.

    Args:
        username (str): Instagram username to validate.
        sf_api_key (str): ScrapeFish API key.

    Returns:
        Optional[str]: User ID if valid, None otherwise.
    """
    params = {
        "api_key": sf_api_key,
        "url": f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}",
        "headers": json.dumps({"x-ig-app-id": "936619743392459"}),
    }

    try:
        response = requests.get("https://scraping.narf.ai/api/v1/", params=params, timeout=30)
        response.raise_for_status()
        profile_data = response.json()
        user = profile_data.get("data", {}).get("user", {})
        is_private = user.get("is_private", False)
        user_id = user.get("id")

        if not user_id:
            print(f"Error: Username '{username}' is invalid.")
            return None

        if is_private:
            print(f"Error: Username '{username}' is private.")
            return None

        return user_id
    except Exception as e:
        print(f"Error validating username '{username}': {e}")
        return None


def parse_page_info(response_json: Dict[str, Any]) -> Dict[str, Union[Optional[bool], Optional[str]]]:
    top_level_key = "graphql" if "graphql" in response_json else "data"
    user_data = response_json[top_level_key].get("user", {})
    page_info = user_data.get("edge_owner_to_timeline_media", {}).get("page_info", {})
    return page_info


def parse_posts(response_json: Dict[str, Any], start_timestamp: int) -> List[Dict[str, Any]]:
    top_level_key = "graphql" if "graphql" in response_json else "data"
    user_data = response_json[top_level_key].get("user", {})
    post_edges = user_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
    posts = []
    for node in post_edges:
        post_json = node.get("node", {})
        timestamp = post_json.get("taken_at_timestamp")

        # Skip posts before the start date
        if timestamp <= start_timestamp:
            continue

        shortcode = post_json.get("shortcode")
        image_url = post_json.get("display_url")
        caption_edges = post_json.get("edge_media_to_caption", {}).get("edges", [])
        description = caption_edges[0].get("node", {}).get("text") if len(caption_edges) > 0 else None
        posts.append({
            "shortcode": shortcode,
            "image_url": image_url,
            "description": description,
            "timestamp": timestamp,
            "date": datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        })
    return posts


def scrape_ig_profile(username: str, sf_api_key: str, start_date: str) -> List[Dict[str, Any]]:
    # Validate username
    user_id = validate_username(username, sf_api_key)
    if not user_id:
        return []

    # Prepare directory for storing post data
    data_dir = os.path.join("test_post_data")
    os.makedirs(data_dir, exist_ok=True)

    # Paths for files
    posts_json_path = os.path.join(data_dir, f"{username}_posts.json")
    posts_csv_path = os.path.join(data_dir, f"{username}_posts.csv")
    last_scraped_path = os.path.join(data_dir, f"{username}_last_scraped.json")

    # Convert start_date to a timestamp
    start_timestamp = int(datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp())

    # Load the last scraped timestamp from a file if available
    if os.path.exists(last_scraped_path):
        with open(last_scraped_path, "r") as file:
            last_scraped = int(datetime.datetime.strptime(json.load(file)["last_scraped"], "%Y-%m-%d %H:%M:%S").timestamp())
        print(f"Last scraped date: {datetime.datetime.utcfromtimestamp(last_scraped)}")
        # Use the later of the last scraped timestamp or the start timestamp
        start_timestamp = max(start_timestamp, last_scraped)
    else:
        print(f"No last scraped date found. Using start_date: {start_date}")

    # Fetch posts
    params = {
        "api_key": sf_api_key,
        "url": f"https://instagram.com/graphql/query/?query_id=17888483320059182&id={user_id}&first=24",
    }

    def request_json(url, params) -> Dict[str, Any]:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()

    response_json = request_json(url="https://scraping.narf.ai/api/v1/", params=params)

    # Parse the first batch of posts
    posts = parse_posts(response_json=response_json, start_timestamp=start_timestamp)
    page_info = parse_page_info(response_json=response_json)

    # Get next page cursor
    end_cursor = page_info.get("end_cursor")
    while end_cursor:
        params["url"] = f"https://instagram.com/graphql/query/?query_id=17888483320059182&id={user_id}&first=24&after={end_cursor}"
        response_json = request_json(url="https://scraping.narf.ai/api/v1/", params=params)
        posts.extend(parse_posts(response_json=response_json, start_timestamp=start_timestamp))
        page_info = parse_page_info(response_json=response_json)
        end_cursor = page_info.get("end_cursor")

    # Save posts to JSON and CSV
    save_to_json_file(posts, posts_json_path)

    # Save the last scraped timestamp to a file
    if posts:
        new_last_scraped = max(post["timestamp"] for post in posts)
        with open(last_scraped_path, "w") as file:
            json.dump({"last_scraped": datetime.datetime.utcfromtimestamp(new_last_scraped).strftime("%Y-%m-%d %H:%M:%S")}, file)
        print(f"Updated last scraped date: {datetime.datetime.utcfromtimestamp(new_last_scraped)}")

    df = pd.DataFrame(posts)
    df.to_csv(posts_csv_path, index=False)
    print(f"Data successfully saved to {posts_csv_path}")

    return posts


def save_to_json_file(data: List[Dict[str, Any]], filename: str) -> None:
    """Saves a list of dictionaries to a JSON file."""
    try:
        if os.path.exists(filename):
            # Append to existing JSON file
            with open(filename, "r") as json_file:
                existing_data = json.load(json_file)
            data = existing_data + data
        with open(filename, "w") as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving data to {filename}: {e}")

def move_json_file(src_path: str, dest_dir: str) -> None:
    """Moves a file to the specified directory."""
    try:
        dest_path = os.path.join(dest_dir, os.path.basename(src_path))
        shutil.move(src_path, dest_path)
        print(f"File moved to {dest_path}")
    except Exception as e:
        print(f"Error moving file {src_path} to {dest_dir}: {e}")