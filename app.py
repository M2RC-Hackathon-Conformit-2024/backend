import os
import jwt
from chainlit.config import config
from typing import Any, Dict
from fastapi.security import OAuth2PasswordBearer
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from chainlit.data import get_data_layer
from chainlit.auth import create_jwt
from chainlit.oauth_providers import get_configured_oauth_providers
from chainlit.user import User
from chainlit.utils import mount_chainlit

from dotenv import load_dotenv

from model import init_db_command, User as Users
load_dotenv()

app = FastAPI()
init_db_command()

reuseable_oauth = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)
SECRET_KEY = os.getenv("CHAINLIT_AUTH_SECRET")
ALGORITHM = "HS256"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.get("/custom-auth")
async def custom_auth():
    # Verify the user's identity with custom logic.

    token = create_jwt(User(identifier="Test User"))
    return JSONResponse({"token": token})

@app.post("/login")
async def login(request: Request):
    body =await request.json()
    try:
        Users.create(
            name = body["name"],
            password = body["password"]
        )
        response = JSONResponse({"code":200})
    except:
        response = JSONResponse({"code":422})
    return response

@app.post("/signIn")
async def signIn(request: Request):
    body =await request.json()
    try:
        user = Users.get(Users.name == body["name"])
        if(user.password == body["password"]):
            token = create_jwt(User(identifier=user.name))
            response = JSONResponse({"code":200, "token":token})
        else:
            response = JSONResponse({"code":422})
    except:
        response = JSONResponse({"code":422})
    return response



async def authenticate_user(request: Request):
    # Passez la requête au reuseable_oauth
    token = await reuseable_oauth(request)  # Appel avec l'objet request
    print("je suis passer par la")
    try:
        dict = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_signature": True},
        )
        del dict["exp"]
        user = User(**dict)
    except Exception as e:
        print("la aussi")
        user = None
    if data_layer := get_data_layer():
        print("la aussi")
        try:
            persisted_user = await data_layer.get_user(user.identifier)
            if persisted_user is None:
                persisted_user = await data_layer.create_user(user)
        except Exception:
            return user

        if user and user.display_name:
            persisted_user.display_name = user.display_name
        return persisted_user
    else:
        return user



@app.get("/custom-auth")
async def custom_auth():
    # Verify the user's identity with custom logic.
    token = create_jwt(User(identifier="Test User"))
    return JSONResponse({"token": token})

# Montée sécurisée de Chainlit avec le middleware de vérification du token
@app.middleware("http")
async def token_verification_middleware(request: Request, call_next):
    user = await authenticate_user(request)  # Passez la requête ici aussi
    if user is None and request.url.path.startswith("/chainlit"):
        response = JSONResponse({"code": 401})
    else:
        response = await call_next(request)
    return response

mount_chainlit(app=app, target="cl_app.py", path="/chainlit")