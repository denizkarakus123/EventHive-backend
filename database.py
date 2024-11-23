from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Table, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from decouple import config

# Database configuration
DATABASE_URL = config("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    # required
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    # optional
    name = Column(String, unique=False, index=False, nullable=True)
    faculty = Column(String, unique=False, index=False, nullable=True)
    year = Column(Integer, unique=False, index=False, nullable=True)
    ispublic = Column(Boolean, unique=False, index=False, nullable=True)
    event = Column(String, unique=False, index=False, nullable=True)

    rsvp = relationship('Event', secondary='people_event', backref='people')


class Organization(Base):
    __tablename__ = "organizations"

    # required
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=False)

    # club info
    location = Column(String, unique=False, index=False, nullable=True)
    faculty = Column(String, unique=False, index=False, nullable=True)
    description = Column(String, unique=False, index=False, nullable=True)

    # socials
    instagram = Column(String, unique=False, index=False, nullable=True)
    facebook = Column(String, unique=False, index=False, nullable=True)
    website = Column(String, unique=False, index=False, nullable=True)
    email = Column(String, unique=False, index=False, nullable=True)

    image = Column(String, unique=False, index=False, nullable=True)

    events = relationship('Event', uselist=True, backref='organization')

class Event(Base):
    __tablename__ = "events"

    # required
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    host_id = Column(Integer, ForeignKey('organizations.id'))
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # optional
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    cost = Column(Integer, nullable=True)
    food = Column(Boolean, nullable=True)
    location = Column(String, nullable=True)
    link = Column(String, nullable=True)


people_event = Table('people_event',
                    Base.metadata,
                    Column('user_id', Integer, ForeignKey('users.id')),
                    Column('event_id', Integer, ForeignKey('events.id'))
                    )

Base.metadata.create_all(engine)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
