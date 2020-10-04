from fastapi.security import OAuth2PasswordRequestForm
from app.services.user import insert_user
from fastapi import APIRouter
from fastapi import Depends, Form, status, HTTPException
from fastapi import Request, Response
from fastapi.templating import Jinja2Templates
from app.models.token import Token
from app.models.user import User
from app.services import user as service
from datetime import datetime, timedelta
from app.configs import general as configs

templates = Jinja2Templates(directory="app/templates/")
router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=configs.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/savenewuser", response_model=User, status_code=201)
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
        print("insert_user error: " + str(e))

@router.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(service.get_current_active_user)):
    return current_user

@router.get("/users/me/items/")
async def read_own_items(current_user: User = Depends(service.get_current_active_user)):
    return [{"item_id": "Foo", "owner": current_user.username}]

@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        'index.html', {"request": request}
    )

@router.get("/logged", response_model=User)
async def logged(request: Request, current_user: User = Depends(service.get_current_active_user)):
    return templates.TemplateResponse(
        'logged.html', {"request": request, "test": "logged :)"}
    )

@router.get("/register")
async def register(request: Request):
    return templates.TemplateResponse(
        'register.html', {"request": request}
    )
