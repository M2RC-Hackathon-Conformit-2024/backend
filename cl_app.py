from langchain_aws import ChatBedrockConverse
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from typing import cast
from context import session_user_cache  # Importe la variable de contexte
import argparse
# from dataclasses import dataclass
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import openai
import chainlit as cl
import os
from dotenv import load_dotenv
import random
import string
from model import conversation_history,current_user

load_dotenv()

openai.api_key = os.environ['OPENAI_API_KEY']
CHROMA_PATH = "chroma"

discusion = [("system","You are a helpful assistant."),("human", "{question}")]

# Prepare the DB.
embedding_function = OpenAIEmbeddings()
db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

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

    # Ajoute le nouveau message de l'utilisateur dans l'historique
    history.append(("human", message.content))
    # Search the DB.
    results = db.similarity_search_with_relevance_scores(message.content, k=5)
    if len(results) == 0 or results[0][1] < 0.7:
        pass
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    # Enregistre le message dans la base de données
    conversation_history.create(
        id_user = id_user,
        session_id = session_id, 
        role = "human", 
        message = message.content)

    # Formate l'historique pour l'inclure dans le prompt
    conversation = "\n".join(f"{role}: {text}" for role, text in history)
    #mettre le contexte ici
    modified_user_message = f"""
    Use only the following context to answer the question without mentioning the context in your answer.

    Context: "{context_text}"

    Question: {message.content}
    Answer:
    """
    msg = cl.Message(content="")

    async for chunk in runnable.astream(
        {"conversation": conversation,"question": modified_user_message},
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
