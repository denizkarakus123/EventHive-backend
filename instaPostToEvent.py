import openai
import pandas as pd
import json
from sqlalchemy.orm import Session
from database import SessionLocal, Event
from dateutil.parser import parse as parse_date
from datetime import datetime

openai.api_key = "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"

def extract_event_data(caption, image_description):
    # Use OpenAI's GPT API to extract event information from Instagram post data
    prompt = f"""
    The following is an Instagram post caption and image description for an event organized by a McGill University club. Extract the event details following the Event Schema below and output it strictly as a JSON object without any additional text or formatting.

    Caption: {caption}
    Image Description: {image_description}

    Event Schema:
    - IsAnEvent (Yes/No)
    - IsInPerson (Yes/No)
    - Location (if in-person)
    - Link (if online)
    - Host (organization)
    - IsFullday (Yes/No)
    - Day
    - Start time, End time (in 24-hour format, e.g., 14:00, 16:00)
    - Event description
    - Event name
    - Event Category (one of these 6: Sports, Arts and Culture, Educational, Social, Charity and Fundraising, Technology and Innovation)

    Ensure the response is a valid JSON object with no additional comments, formatting, or code block syntax.
    """

    try:
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

        # Extract the content of the response
        result = response["choices"][0]["message"]["content"].strip()

        # Ensure the response is properly formatted as JSON
        if result.startswith("```json"):
            result = result.lstrip("```json").rstrip("```").strip()

        return json.loads(result)

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from OpenAI response: {e}")
        print("Response content:", response["choices"][0]["message"]["content"])
        return None
    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return None

# Load CSV data
csv_file_path = "test_post_data/mcgill_ecsess_posts.csv"  # Replace with your CSV file path
data = pd.read_csv(csv_file_path)

# Extract event data from each row and store results
events = []
for index, row in data.iterrows():
    caption = row['description']
    image_description = ""  # Assuming image description is not provided in the CSV
    event_data = extract_event_data(caption, image_description)
    if event_data:
        events.append(event_data)

# Save extracted event data to a new JSON file
with open('extracted_events.json', 'w') as json_file:
    json.dump(events, json_file, indent=4)

print("Event data extraction completed and saved to 'extracted_events.json'")

def save_event_to_db(event_details):
    """
    Save the extracted event details to the database, preventing duplicates.
    """
    db: Session = SessionLocal()  # Create a new database session

    try:
        # Ensure the 'day' field exists and is not None
        day = event_details.get("Day")
        if not day:
            print(f"Missing 'Day' field in event details: {event_details}")
            return

        # Parse and standardize the date and time
        try:
            parsed_date = parse_date(day)  # Parse natural language date
            standardized_date = parsed_date.strftime("%Y-%m-%d")  # Convert to %Y-%m-%d format
        except Exception as e:
            print(f"Error parsing date: {day} - {e}")
            return

        # Handle time fields flexibly
        start_time = event_details.get("Start time")
        end_time = event_details.get("End time")
        is_full_day = event_details.get("IsFullday") == "Yes"

        if is_full_day:
            # For full-day events
            start_datetime = parsed_date
            end_datetime = parsed_date
        elif not start_time or not end_time or "late" in (start_time.lower(), end_time.lower(), "tbd" in (start_time.lower(), end_time.lower())):
            # For events without specific start/end times or vague times (e.g., 'late', 'TBD')
            start_datetime = parsed_date
            end_datetime = parsed_date
        else:
            try:
                # Combine standardized date with start and end times
                start_datetime = datetime.strptime(
                    f"{standardized_date} {start_time}", "%Y-%m-%d %H:%M"
                )
                end_datetime = datetime.strptime(
                    f"{standardized_date} {end_time}", "%Y-%m-%d %H:%M"
                )
            except Exception as e:
                print(f"Error parsing time: {start_time} or {end_time} - {e}")
                return

        # Check for duplicate events
        existing_event = (
            db.query(Event)
            .filter(
                Event.name == event_details.get("Event name"),
                Event.location == event_details.get("Location"),
                Event.start_date == start_datetime,
            )
            .first()
        )
        if existing_event:
            print(f"Duplicate event found: {existing_event.name}. Skipping...")
            return

        # Create a new Event instance
        new_event = Event(
            name=event_details.get("Event name"),
            location=event_details.get("Location"),
            start_date=start_datetime,
            end_date=end_datetime,
            description=event_details.get("Event description"),
        )
        # Add and commit the new event
        db.add(new_event)
        db.commit()
        print("Event saved to database:", new_event)
    except Exception as e:
        print(f"Error saving to database: {e}")
        db.rollback()
    finally:
        db.close()  # Close the database session

# Load CSV data
csv_file_path = "test_post_data/mcgill_ecsess_posts.csv"  # Replace with your CSV file path
data = pd.read_csv(csv_file_path)

# Extract event data from each row and store results
for index, row in data.iterrows():
    caption = row['description']
    image_description = ""  # Assuming image description is not provided in the CSV
    event_data = extract_event_data(caption, image_description)
    if event_data:
        save_event_to_db(event_data)

print("Event data extraction and database saving completed.")
