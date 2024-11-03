from langchain_aws import ChatBedrockConverse
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from typing import cast
from context import session_user_cache  # Importe la variable de contexte

import chainlit as cl

from dotenv import load_dotenv
import random
import string
from model import conversation_history,current_user

load_dotenv()

discusion = [("system","You are a helpful assistant."),("human", "{question}")]

def generate_random_id(length=8):
    characters = string.ascii_letters + string.digits  # Lettres (majuscules et minuscules) + chiffres
    random_id = ''.join(random.choice(characters) for _ in range(length))
    return random_id

@cl.on_chat_start
async def on_chat_start():
    llm = ChatBedrockConverse(
        model="anthropic.claude-3-sonnet-20240229-v1:0",
        region_name="us-west-2",
        temperature=0,
        max_tokens=None
    )
    # Initialise un historique de conversation vide pour la session
    cl.user_session.set("history", [])
    
    user = current_user.select().first()
    # Stocke l'ID de session unique
    session_id = generate_random_id(12)

    cl.user_session.set("id_user", user.user_id)
    cl.user_session.set("session_id", session_id)

    prompt = ChatPromptTemplate.from_messages(discusion)
    runnable = prompt | llm | StrOutputParser()
    cl.user_session.set("runnable", runnable)

    current_user.delete().execute()
    await cl.Message(content="Connected to Chainlit!").send()


@cl.on_message
async def on_message(message: cl.Message):
    runnable = cast(Runnable, cl.user_session.get(
        "runnable"))  # type: Runnable
    history = cl.user_session.get("history")
    session_id = cl.user_session.get("session_id")
    id_user = cl.user_session.get("id_user")
    print(id_user)

    # Ajoute le nouveau message de l'utilisateur dans l'historique
    history.append(("human", message.content))

        # Enregistre le message dans la base de données
    conversation_history.create(
        id_user = id_user,
        session_id = session_id, 
        role = "human", 
        message = message.content)

    # Formate l'historique pour l'inclure dans le prompt
    conversation = "\n".join(f"{role}: {text}" for role, text in history)
    msg = cl.Message(content="")

    async for chunk in runnable.astream(
        {"conversation": conversation,"question": message.content},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await msg.stream_token(chunk)
    await msg.send()
# Ajoute la réponse de l'assistant à l'historique et enregistre dans la base de données
    history.append(("assistant", msg.content))
    conversation_history.create(
        id_user = id_user,
        session_id = session_id, 
        role = "assistant", 
        message = msg.content
    )

    # Sauvegarde l'historique mis à jour dans la session
    cl.user_session.set("history", history)
