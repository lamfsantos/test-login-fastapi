from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi import Request, Response
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import sqlite3
from sqlite3 import Error

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "f639a3dd658dcb9f6fdae5ed949460f892e67980499826263b355aed4af6cb72"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

templates = Jinja2Templates(directory=".")

############ db
# fake_users_db = {
#     "johndoe": {
#         "username": "johndoe",
#         "full_name": "John Doe",
#         "email": "johndoe@example.com",
#         "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
#         "disabled": False,
#     }
# }
#
# print(fake_users_db)
# print(type(fake_users_db))

database = r"pythonsqlite.db"

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn

def find_all():
    conn = create_connection(database)

    cur = conn.cursor()
    cur.execute("SELECT username, full_name, email, hashed_password, disabled FROM users")

    rows = cur.fetchall()

    conn.close()

    return rows

def insert(username: str, password: str, email: str, full_name: str):
    conn = create_connection(database)

    sql = ''' INSERT INTO users(username,full_name,email,hashed_password,disabled)
              VALUES(?,?,?,?,?) '''

    cur = conn.cursor()
    cur.execute(sql, (username, full_name, email, password, 0, ))
    conn.commit()
    return cur.lastrowid

def list_to_dict(users_list: list):
    users_dict = {}

    for user in users_list:
        users_dict[user[0]] = {
            "username": user[0],
            "fullname": user[1],
            "email": user[2],
            "hashed_password": user[3],
            "disabled": (False if user[4]==0 else True)
        }
    #users_dict['create_access_token'] = {'name': 'luiz'}
    return users_dict

fake_users_db = {}

def update_in_mamory_db():
    global fake_users_db
    fake_users_db = find_all()
    fake_users_db = list_to_dict(fake_users_db)

    print(fake_users_db)

update_in_mamory_db()

############

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)

def insert_user(username: str, password: str, email: str, full_name: str):
    try:
        insert(username, get_password_hash(password), email, full_name)
        update_in_mamory_db()
    except Exception as e:
        print(e)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": "Foo", "owner": current_user.username}]

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        'index.html', {"request": request}
    )

@app.get("/logged", response_model=User)
async def logged(request: Request, current_user: User = Depends(get_current_active_user)):
    return templates.TemplateResponse(
        'logged.html', {"request": request, "test": "logged :)"}
    )

@app.get("/register")
async def register(request: Request):
    return templates.TemplateResponse(
        'register.html', {"request": request}
    )

@app.post("/savenewuser", response_model=User, status_code=201)
async def save_new_user(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...)
    ):

    try:
        insert_user(username, password, email, full_name)
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        print(e)
