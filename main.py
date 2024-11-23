from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from decouple import config

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

# Mock database
fake_users_db = {}

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

def authenticate_user(username: str, password: str):
    user = fake_users_db.get(username)
    if not user or not verify_password(password, user["password"]):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in fake_users_db:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return fake_users_db[username]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Models
class UserRegister(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: Optional[str]

class Token(BaseModel):
    access_token: str
    token_type: str

# Routes
@app.post("/register", status_code=201)
async def register(user: UserRegister):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_password = get_password_hash(user.password)
    fake_users_db[user.username] = {"username": user.username, "password": hashed_password}
    return {"message": "User registered successfully"}

@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/profile")
async def profile(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"]}

@app.put("/update-profile")
async def update_profile(update: UserUpdate, current_user: dict = Depends(get_current_user)):
    if update.username:
        fake_users_db[current_user["username"]]["username"] = update.username
        current_user["username"] = update.username
    return {"message": "Profile updated successfully"}