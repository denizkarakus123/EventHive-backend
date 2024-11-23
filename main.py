from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from decouple import config
from sqlalchemy.orm import Session
from database import get_db, User
from schemas import UserCreate, OrganizationCreate, OrganizationRead, EventCreate, EventRead, GroupedEventsResponse
from database import Event, Organization
from collections import defaultdict

# Configuration
SECRET_KEY = config("SECRET_KEY", default="your_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

origins = [
    "http://localhost",
    "http://localhost:5173"
]

# FastAPI instance
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specified origins
    allow_credentials=True,  # Allows cookies and other credentials
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")



# Utility functions
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(username: str, password: str, db: Session) -> User | None:
    # Query the database for the user
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Models

class UserUpdate(BaseModel):
    username: Optional[str]
    name: Optional[str]
    faculty: Optional[str]
    ispublic: Optional[bool]
    event: Optional[str]
    year: Optional[int]


class Token(BaseModel):
    access_token: str
    token_type: str

# Routes
@app.post("/register", status_code=201)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash the password and store the user in the database
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully"}

@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Generate a JWT token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/profile")
async def profile(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "name": current_user.name, "faculty": current_user.faculty, "year": current_user.year, "ispublic": current_user.ispublic, "event": current_user.event, "event_attendance": current_user.rsvp}

@app.get("/users/{user_id}")
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,  # Include other user details if applicable
        "faculty": user.faculty,  # Assuming these fields exist
        "year": user.year,
        "ispublic": user.ispublic,
        "event": user.event,
        "event_attendance": user.rsvp
    }



@app.put("/update-profile")
async def update_profile(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),):
    # Update the fields if they are provided
    if update.username:
        # Check if the new username already exists
        existing_user = db.query(User).filter(User.username == update.username).first()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Username already exists")
        current_user.username = update.username
    
    if update.name:
        current_user.name = update.name
    
    if update.faculty:
        current_user.faculty = update.faculty
    
    if update.ispublic is not None:  # Check for None to allow setting False
        current_user.ispublic = update.ispublic

    if update.event:
        current_user.event = update.event
    
    if update.year:
        current_user.year = update.year

    db.commit()
    db.refresh(current_user)

    return {"message": "Profile updated successfully"}

# Create a new event
@app.post("/events/", response_model=EventRead)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    host = db.query(Organization).filter(Organization.id == event.host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host organization not found")
    new_event = Event(**event.dict())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

# Retrieve an event by ID
@app.get("/events/{event_id}", response_model=EventRead)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

# List all events
@app.get("/events/", response_model=list[EventRead])
def list_events(db: Session = Depends(get_db)):
    return(db.query(Event).all())

# List all events grouped by year, month, and day
@app.get("/groupedevents/", response_model=GroupedEventsResponse)
def list_events(db: Session = Depends(get_db)):
    # Get all events, sorted by start_date (ascending)
    events = db.query(Event).order_by(Event.start_date.asc()).all()

    # If no events are found, return an empty response
    if not events:
        return GroupedEventsResponse(events_by_year={})

    # Initialize a nested defaultdict to group events by year, month, and day
    grouped_events = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    # Group events by year, month, and day
    for event in events:
        event_date = event.start_date
        year = event_date.year
        month = event_date.month
        day = event_date.day

        # Append the event to the appropriate group in the nested defaultdict
        grouped_events[year][month][day].append(event)

    # Convert the grouped data into the desired format
    # We need to convert the defaultdict to a regular dict for Pydantic validation
    
    grouped_event_dict = {
        year: {
            month: {
                day: [event for event in events_in_day]
                for day, events_in_day in months.items()
            }
            for month, months in months_and_years.items()
        }
        for year, months_and_years in grouped_events.items()
    }

    # Return the grouped events as a response
    return GroupedEventsResponse(events_by_year=grouped_event_dict)

# Create a new organization
@app.post("/organizations/", response_model=OrganizationRead)
def create_organization(org: OrganizationCreate, db: Session = Depends(get_db)):
    db_org = db.query(Organization).filter(Organization.name == org.name).first()
    if db_org:
        raise HTTPException(status_code=400, detail="Organization name already registered")
    new_org = Organization(**org.dict())
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    return new_org

# Retrieve an organization by ID
@app.get("/organizations/{org_id}", response_model=OrganizationRead)
def get_organization(org_id: int, db: Session = Depends(get_db)):
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization

# List all organizations
@app.get("/organizations/", response_model=list[OrganizationRead])
def list_organizations(db: Session = Depends(get_db)):
    return db.query(Organization).all()

#RSVP to an event
@app.post("/rsvp/{event_id}", )
async def rsvp_event(event_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if the event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if the user has already RSVPed to the event
    if event in current_user.rsvp:
        raise HTTPException(status_code=400, detail="You have already RSVPed to this event")

    # Add RSVP (associate user with the event)
    current_user.rsvp.append(event)
    db.commit()

    return {
        "message": "RSVP successful",
        "event_id": event.id,
        "user_id": current_user.id
    }


# Cancel RSVP to an event
@app.delete("/rsvp/{event_id}")
async def cancel_rsvp(event_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if the event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if the user has RSVPed to the event
    if event not in current_user.rsvp:
        raise HTTPException(status_code=400, detail="You have not RSVPed to this event")

    # Remove RSVP (disassociate user from the event)
    current_user.rsvp.remove(event)
    db.commit()

    return {
        "message": "RSVP canceled",
        "event_id": event.id,
        "user_id": current_user.id
    }

# Retrieve all events RSVPed by the current user
@app.get("/rsvp/", response_model=list[EventRead])
async def get_rsvp_events(current_user: User = Depends(get_current_user)):
    # Retrieve all RSVPed events for the user
    return current_user.rsvp
