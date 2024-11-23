from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Shared base schema
class UserBase(BaseModel):
    username: str
    name: Optional[str] = None
    faculty: Optional[str] = None
    year: Optional[int] = None
    ispublic: Optional[bool] = None
    event: Optional[str] = None

# Schema for creating a user
class UserCreate(UserBase):
    password: str

# Schema for reading a user (e.g., response)
class UserResponse(UserBase):
    id: int
    rsvp: List[int]  # List of event IDs

    class Config:
        orm_mode = True


# Shared base schema
class OrganizationBase(BaseModel):
    name: str
    location: Optional[str] = None
    faculty: Optional[str] = None
    description: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    image: Optional[str] = None

# Schema for creating an organization
class OrganizationCreate(OrganizationBase):
    pass

# Schema for reading an organization (e.g., response)
class OrganizationRead(OrganizationBase):
    id: int
    events: List[int]  # List of event IDs

    class Config:
        orm_mode = True


# Shared base schema
class EventBase(BaseModel):
    name: str
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None
    category: Optional[str] = None
    cost: Optional[int] = None
    food: Optional[bool] = None
    location: Optional[str] = None
    link: Optional[str] = None

# Schema for creating an event
class EventCreate(EventBase):
    host_id: int  # ID of the hosting organization

# Schema for reading an event (e.g., response)
class EventRead(EventBase):
    id: int
    host_id: int
    people: List[int]  # List of user IDs attending the event

    class Config:
        orm_mode = True
