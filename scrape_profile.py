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
    """
    Parses posts from the response JSON and filters them by a start timestamp.

    Args:
        response_json (Dict[str, Any]): The JSON response from Instagram.
        start_timestamp (int): The minimum timestamp for filtering posts.

    Returns:
        List[Dict[str, Any]]: A list of posts created after the start timestamp.
    """
    top_level_key = "graphql" if "graphql" in response_json else "data"
    user_data = response_json[top_level_key].get("user", {})
    post_edges = user_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
    posts = []
    for node in post_edges:
        post_json = node.get("node", {})
        timestamp = post_json.get("taken_at_timestamp")

        # Skip posts before the start date and time
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


def scrape_ig_profile(username: str, sf_api_key: str, start_datetime: str) -> List[Dict[str, Any]]:
    """
    Scrapes Instagram posts for a specific username and filters by a start datetime.

    Args:
        username (str): Instagram username.
        sf_api_key (str): ScrapeFish API key.
        start_datetime (str): The minimum datetime for filtering posts (format: YYYY-MM-DD HH:MM:SS).

    Returns:
        List[Dict[str, Any]]: A list of posts created after the start datetime.
    """
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

    # Convert start_datetime to a timestamp
    start_timestamp = int(datetime.datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S").timestamp())

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

    return posts


def save_to_json_file(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Saves a list of dictionaries to a JSON file, appending new data if the file already exists.

    Args:
        data (List[Dict[str, Any]]): List of posts to save.
        filename (str): Path to the JSON file.
    """
    try:
        if os.path.exists(filename):
            # Load the existing JSON data
            with open(filename, "r") as json_file:
                existing_data = json.load(json_file)

            # Avoid duplicate entries by checking unique identifiers (e.g., 'shortcode')
            existing_shortcodes = {post['shortcode'] for post in existing_data}
            new_data = [post for post in data if post['shortcode'] not in existing_shortcodes]

            # Append new posts to existing data
            updated_data = existing_data + new_data
        else:
            # If the file doesn't exist, initialize with the new data
            updated_data = data

        # Write the updated data back to the file
        with open(filename, "w") as json_file:
            json.dump(updated_data, json_file, indent=4)

        print(f"Data successfully saved to {filename}. Total posts: {len(updated_data)}")
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
