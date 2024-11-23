import openai
import json
from sqlalchemy.orm import Session
from database import SessionLocal, Event
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dateutil.parser import parse as parse_date
from datetime import datetime
import base64
import os

# OpenAI API Key
openai.api_key = "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"  # Replace with your OpenAI API key

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def get_credentials():
    """
    Get credentials for Gmail API, refreshing them if needed.
    If no valid credentials exist, initiate the OAuth flow.
    """
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token_file:
                json.dump({
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                }, token_file)
        return creds

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=8001, access_type='offline', prompt='consent')

    with open(TOKEN_FILE, 'w') as token_file:
        json.dump({
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }, token_file)

    return creds

def get_email_content():
    """Fetch email content using Gmail API."""
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)

    # Get the list of emails
    results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    messages = results.get('messages', [])

    email_bodies = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        payload = msg['payload']
        parts = payload.get("parts")
        body = None

        # Decode email content
        if parts:
            for part in parts:
                if part["mimeType"] == "text/plain":
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode()
                    break

        if body:
            email_bodies.append(body)
    return email_bodies

def parse_email_with_chatgpt(email_body):
    """Parse email content into structured event details."""
    prompt = f"""
    You are an AI that parses email content into structured data for events.
    Extract the following fields from the provided email:
    - IsAnEvent (Yes/No)
    - IsInPerson (Yes/No)
    - Location (if in-person)
    - Link (if online)
    - Host (organization)
    - Event Name
    - Date
    - Start Time
    - End Time
    - Event Category (one of these: Social, Academic, Sports, Club, Professional)

    If the email does not describe an event, set "is_an_event" to "No" and leave all other fields blank.

    Here is the email content:
    "{email_body}"

    Return the extracted details as a JSON object with the following keys:
    - is_an_event
    - is_in_person
    - location
    - link
    - host
    - event_name
    - date
    - start_time
    - end_time
    - category
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
        )
        result = response["choices"][0]["message"]["content"]
        return json.loads(result)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from OpenAI: {e}")
        print(f"Raw response: {response['choices'][0]['message']['content']}")
        return None
    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return None

def save_event_to_db(event_details):
    """Save the extracted event details to the database, preventing duplicates."""
    db: Session = SessionLocal()

    try:
        if event_details.get("is_an_event") != "Yes":
            print("This email is not an event. Skipping...")
            return

        parsed_date = parse_date(event_details.get("date"))
        standardized_date = parsed_date.strftime("%Y-%m-%d")

        start_datetime = datetime.strptime(
            f"{standardized_date} {event_details.get('start_time')}", "%Y-%m-%d %I:%M %p"
        )
        end_datetime = datetime.strptime(
            f"{standardized_date} {event_details.get('end_time')}", "%Y-%m-%d %I:%M %p"
        )

        # Check for duplicate events (consider online and in-person separately)
        if event_details.get("is_in_person") == "Yes":
            # Check for duplicates for in-person events
            existing_event = (
                db.query(Event)
                .filter(
                    Event.name.ilike(f"%{event_details.get('event_name')}%"),
                    Event.location.ilike(f"%{event_details.get('location')}%"),
                    Event.start_date == start_datetime,
                )
                .first()
            )
        else:
            # Check for duplicates for online events
            existing_event = (
                db.query(Event)
                .filter(
                    Event.name.ilike(f"%{event_details.get('event_name')}%"),
                    Event.link.ilike(f"%{event_details.get('link')}%"),
                    Event.start_date == start_datetime,
                )
                .first()
            )

        if existing_event:
            print(f"Duplicate event found: {existing_event.name}. Skipping...")
            return

        # Add location or link based on event type
        location = event_details.get("location") if event_details.get("is_in_person") == "Yes" else None
        link = event_details.get("link") if event_details.get("is_in_person") == "No" else None

        # Create a new Event instance with category, location, and link
        new_event = Event(
            name=event_details.get("event_name"),
            location=location,
            link=link,
            start_date=start_datetime,
            end_date=end_datetime,
            description=f"Organized by {event_details.get('host')}",
            category=event_details.get("category"),  # Add category
        )
        db.add(new_event)
        db.commit()
        print("Event saved to database:", new_event)
    except Exception as e:
        print(f"Error saving to database: {e}")
        db.rollback()
    finally:
        db.close()

def process_multiple_emails():
    """Fetch emails from Gmail and process them."""
    email_bodies = get_email_content()
    for email_body in email_bodies:
        event_details = parse_email_with_chatgpt(email_body)
        if event_details:
            print("Extracted Event Details:", event_details)
            save_event_to_db(event_details)
        else:
            print("Failed to parse email:", email_body)

if __name__ == "__main__":
    process_multiple_emails()
