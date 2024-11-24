import openai
import json
from sqlalchemy.orm import Session
from database import SessionLocal, Event
from dateutil.parser import parse as parse_date
from datetime import datetime
from database import Organization

openai.api_key = "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"



def extract_event_data(caption, image_description):
    # extract event information from instagram post data
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
        # get the structured response
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

        # Get or create the organization
        host_name = event_details.get("Host")
        if not host_name:
            print(f"Missing 'Host' field in event details: {event_details}")
            return

        # Check if the organization exists
        organization = db.query(Organization).filter(Organization.name == host_name).first()
        if not organization:
            # Create a new organization if it doesn't exist
            organization = Organization(name=host_name)
            db.add(organization)
            db.commit()  # Commit to get the organization ID
            db.refresh(organization)

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
            host_id=organization.id,  # Use the organization's ID as host_id
            start_date=start_datetime,
            end_date=end_datetime,
            description=event_details.get("Event description"),
            category=event_details.get("Event Category"),
            cost=event_details.get("Cost", 0),
            food=True if event_details.get("Food") == True else False,
            location=event_details.get("Location"),
            link=event_details.get("Link") if "Link" in event_details else None,
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


file_paths = [
    "test_post_data/json_files/acecmcgill_posts.json",
    "test_post_data/json_files/ahcssamcgill_posts.json",
    "test_post_data/json_files/amnestymcgill_posts.json",
    "test_post_data/json_files/ceusmcgill_posts.json",
    "test_post_data/json_files/clashsa.mcgill_posts.json",
    "test_post_data/json_files/desamcgill_posts.json",
    "test_post_data/json_files/engineeringfrosh_posts.json",
    "test_post_data/json_files/esamcgill_posts.json",
    "test_post_data/json_files/genderequalitymcgill_posts.json",
    "test_post_data/json_files/gertstilithurts_posts.json",
    "test_post_data/json_files/girlswhocodemcgill_posts.json",
    "test_post_data/json_files/gsfssamcgill_posts.json",
    "test_post_data/json_files/hcsmcgill_posts.json",
    "test_post_data/json_files/irsaminc_posts.json",
    "test_post_data/json_files/isac_mcgill_posts.json",
    "test_post_data/json_files/isp.mcgill_posts.json",
    "test_post_data/json_files/lapsa.mcgill_posts.json",
    "test_post_data/json_files/linguamcgill_posts.json",
    "test_post_data/json_files/makeawishmcgill_posts.json",
    "test_post_data/json_files/mame_mcgill_posts.json",
    "test_post_data/json_files/mcgill_ecsess_posts.json",
    "test_post_data/json_files/mcgill_mdvfs_posts.json",
    "test_post_data/json_files/mcgill_rocket_team_posts.json",
    "test_post_data/json_files/mcgill_rsus_posts.json",
    "test_post_data/json_files/mcgill.asa_posts.json",
    "test_post_data/json_files/mcgill.cssa_posts.json",
    "test_post_data/json_files/mcgill.enggames_posts.json",
    "test_post_data/json_files/mcgill.engineersinaction_posts.json",
    "test_post_data/json_files/mcgill.mining_posts.json",
    "test_post_data/json_files/mcgill.ucda_posts.json",
    "test_post_data/json_files/mcgillarts_posts.json",
    "test_post_data/json_files/mcgillartsoasis_posts.json",
    "test_post_data/json_files/mcgillcampusstore_posts.json",
    "test_post_data/json_files/mcgillcodejam_posts.json",
    "test_post_data/json_files/mcgillconcretecanoe_posts.json",
    "test_post_data/json_files/mcgillcss_posts.json",
    "test_post_data/json_files/mcgillelate_posts.json",
    "test_post_data/json_files/mcgilleng_posts.json",
    "test_post_data/json_files/mcgillengine_posts.json",
    "test_post_data/json_files/mcgilleus_posts.json",
    "test_post_data/json_files/mcgillfamilymed_posts.json",
    "test_post_data/json_files/mcgillmusiclibrary_posts.json",
    "test_post_data/json_files/mcgillnourish_posts.json",
    "test_post_data/json_files/mcgillrobotics_posts.json",
    "test_post_data/json_files/mcgillscilearn_posts.json",
    "test_post_data/json_files/mcgillstuserv_posts.json",
    "test_post_data/json_files/mcgillsus_posts.json",
    "test_post_data/json_files/mcgillu_posts.json",
    "test_post_data/json_files/mec_mcgill_posts.json",
    "test_post_data/json_files/mpsa.mcgill_posts.json",
    "test_post_data/json_files/msert.mcgill_posts.json",
    "test_post_data/json_files/nightlinemcgill_posts.json",
    "test_post_data/json_files/nsbemcgill_posts.json",
    "test_post_data/json_files/onthetablemag_posts.json",
    "test_post_data/json_files/playerstheatremcgill_posts.json",
    "test_post_data/json_files/powemcgill_posts.json",
    "test_post_data/json_files/queermcgill_posts.json",
    "test_post_data/json_files/russmcgill_posts.json",
    "test_post_data/json_files/seam_mcgill_posts.json",
    "test_post_data/json_files/ssa.mcgill_posts.json",
    "test_post_data/json_files/ssmuaeum_posts.json",
    "test_post_data/json_files/studentsinmind_posts.json",
    "test_post_data/json_files/sumsmcgill_posts.json",
    "test_post_data/json_files/susafterhours_posts.json",
    "test_post_data/json_files/wiismcgill_posts.json",
    "test_post_data/json_files/wimessamcgill_posts.json"
]


# Load JSON data
for json_file_path in file_paths:
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