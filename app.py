import os
import chainlit as cl
from fastapi import WebSocket
import jwt
from uuid import uuid4
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
from context import session_user_cache  # Importe la variable de contexte
from peewee import fn
from dotenv import load_dotenv

from model import init_db_command, User as Users , current_user, conversation_history as cs
load_dotenv()

app = FastAPI()
init_db_command()


reuseable_oauth = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)
SECRET_KEY = os.getenv("CHAINLIT_AUTH_SECRET")
ALGORITHM = "HS256"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173", "http://localhost/chainlit/ws/socket.io"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/register")
async def register(request: Request):
    body =await request.json()
    print(body)
    try:
        Users.create(
            email = body["email"],
            password = body["password"]
        )
        response = JSONResponse({"code":200})
    except Exception as e:
        print(e)
        response = JSONResponse({"code":422})
    return response

@app.post("/login")
async def login(request: Request):
    body =await request.json()
    try:
        user = Users.get(Users.email == body["email"])
        if(user.password == body["password"]):
            token = create_jwt(User(identifier=user.email))
            response = JSONResponse({"code":200, "token":token})
        else:
            response = JSONResponse({"code":422})
    except:
        response = JSONResponse({"code":422})
    return response





async def authenticate_user(request: Request):
    # Passez la requête au reuseable_oauth
    token = await reuseable_oauth(request)  # Appel avec l'objet request
    print("Le token est: ", token)
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
        user = None
    if data_layer := get_data_layer():
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



'''
# Montée sécurisée de Chainlit avec le middleware de vérification du token
@app.middleware("http")
async def token_verification_middleware(request: Request, call_next):
    user = await authenticate_user(request)  # Passez la requête ici aussi
    if user is None and request.url.path.startswith("/chainlit"):
        response = JSONResponse({"code": 401})
        #response = await call_next(request)
    else:
        response = await call_next(request)
    return response
'''

@app.get("/get_conversation")
async def getConversation(request: Request):
    user = await authenticate_user(request)
    if user is None:
        return JSONResponse({"code":401})
    else:
        try:
            user_m = Users.get(Users.email == user.identifier)
            id_user = user_m.id
            subquery = (cs.select(cs.id_user, cs.session_id, fn.MIN(cs.id).alias('min_id'))
                        .where(cs.id_user == id_user)
                        .group_by(cs.id_user, cs.session_id))
            query = (cs.select().join(subquery, on=(cs.id == subquery.c.min_id)))
            response = []
            for row in query.dicts():
                response.append(row)
            return JSONResponse(response)
        except:
            return JSONResponse({"code":401})

@app.get("/get_conversations/{session_id}")
async def get_conversations(session_id: str, request: Request):
    user = await authenticate_user(request)
    if user is None:
        return JSONResponse({"code":401})
    else:
        try:
            user_m = Users.get(Users.email == user.identifier)
            id_user = user_m.id
            query = cs.select().where(cs.id_user == id_user and cs.session_id == session_id)
            response = []
            for row in query.dicts():
                response.append(row)
            return JSONResponse(response)
        except:
            return JSONResponse({"code":401})

@app.middleware("http")
async def token_verification_middleware(request: Request, call_next):
    # Laisse passer toutes les requêtes OPTIONS sans vérification de token (nécessaire pour CORS)
    if request.method == "OPTIONS":
        return await call_next(request)

    # Vérifie le token pour toutes les autres requêtes
    user = await authenticate_user(request)
    if user is None and request.url.path.startswith("/chainlit"):
        return JSONResponse({"code": 401})
    if request.url.path.startswith("/chainlit"):
        try:
            user_m = Users.get(Users.email == user.identifier)
            current_user.create(user_id = user_m.id)
        except:
            print(user.identifier)
    return await call_next(request)


mount_chainlit(app=app, target="cl_app.py", path="/chainlit")