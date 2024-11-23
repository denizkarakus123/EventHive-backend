import openai
import pandas as pd
import json

openai.api_key = "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"

def extract_event_data(caption, image_description):
    # Use OpenAI's GPT API to extract event information from Instagram post data
    prompt = f"""
    The following is an Instagram post caption and image description for an event organized by a McGill University club. Extract the event details following the Event Schema below.

    Caption: {caption}
    Image Description: {image_description}

    Event Schema:
    IsAnEvent? (Yes/No)
    If not:
        Don't include this post in the database, exit.
    IsInPerson? (Yes/No)
    If yes:
        Location (e.g., McGill University Arts Building, Room 101)
    Else:
        Link (e.g., Zoom or Google Meet link)
    Host (organization):
    IsFullday? (Yes/No)
    If yes:
        Start day, end day
    If no:
        Day
    Start time, end time (in 24-hour format, e.g., 14:00, 16:00)
    Event description:
    Event name:
    Event Category (one of these 6):
    Sports, Arts and Culture, Educational, Social, Charity and Fundraising, Technology and Innovation

    Output the information in a structured JSON format.
    """

    # Send the prompt to ChatGPT to get the structured response
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.5
    )
    # Parse response and return extracted event details
    return response.choices[0].message['content'].strip()

# Load CSV data
csv_file_path = "test_post_data/mcgill_ecsess_posts.csv"  # Replace with your CSV file path
data = pd.read_csv(csv_file_path)

# Extract event data from each row and store results
events = []
for index, row in data.iterrows():
    caption = row['description']
    image_description = ""  # Assuming image description is not provided in the CSV
    event_data = extract_event_data(caption, image_description)
    try:
        event_json = json.loads(event_data)
        events.append(event_json)
    except json.JSONDecodeError:
        print(f"Error decoding JSON for row {index}: {event_data}")

# Save extracted event data to a new JSON file
with open('extracted_events.json', 'w') as json_file:
    json.dump(events, json_file, indent=4)

print("Event data extraction completed and saved to 'extracted_events.json'")
