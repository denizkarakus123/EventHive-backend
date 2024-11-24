import openai
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
    - Event name
    - Event description
    - Event Category (one of these 5: Social, Academic, Sports, Club, Professional)

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
        if result.startswith("json"):
            result = result.lstrip("json").rstrip("").strip()

        return json.loads(result)

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from OpenAI response: {e}")
        print("Response content:", response["choices"][0]["message"]["content"])
        return None
    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return None

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
        elif not start_time or not end_time or "late" in (start_time.lower(), end_time.lower()) or "tbd" in (start_time.lower(), end_time.lower()):
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
                # Default to full day if time cannot be parsed
                start_datetime = parsed_date
                end_datetime = parsed_date
        
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
            #description=event_details.get("Event description"),
            category=event_details.get("Event Category"),        )
        # Add and commit the new event
        db.add(new_event)
        db.commit()
        print("Event saved to database:", new_event)
    except Exception as e:
        print(f"Error saving to database: {e}")
        db.rollback()
    finally:
        db.close()  # Close the database session

# Load JSON data
json_file_path = "test_post_data/mcgill_ecsess_posts.json"  # Replace with your JSON file path
with open(json_file_path, 'r') as json_file:
    data = json.load(json_file)

# Extract event data from each item in JSON and store results
for item in data:
    caption = item['description']
    image_description = item.get('image_description', "")  # Assuming image description may or may not be provided
    event_data = extract_event_data(caption, image_description)
    if event_data:
        save_event_to_db(event_data)

print("Event data extraction and database saving completed.")