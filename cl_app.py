from langchain_aws import ChatBedrockConverse
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from typing import cast, Optional, Dict
from app import authenticate_user

import chainlit as cl

from dotenv import load_dotenv

load_dotenv()


#Lorsque le chat est lancer



@cl.on_chat_start
async def on_chat_start():
    llm = ChatBedrockConverse(
        model="anthropic.claude-3-sonnet-20240229-v1:0",
        region_name="us-west-2",
        temperature=0,
        max_tokens=None
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant.",
            ),
            ("human", "{question}"),
        ]
    )
    runnable = prompt | llm | StrOutputParser()
    cl.user_session.set("runnable", runnable)

    await cl.Message(content="Vous vous etes connectes!").send()


#la fonction qui suit sera exécutée chaque fois qu'un nouveau message est reçu de l'utilisateur pendant la conversation.
@cl.on_message
async def on_message(message: cl.Message):
    runnable = cast(Runnable, cl.user_session.get(
        "runnable"))  # type: Runnable

    msg = cl.Message(content="")

    async for chunk in runnable.astream(
        {"question": message.content},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await msg.stream_token(chunk)

    await msg.send()



