from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from chainlit.auth import create_jwt
from chainlit.user import User
from chainlit.utils import mount_chainlit

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

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

mount_chainlit(app=app, target="cl_app.py", path="/chainlit")
