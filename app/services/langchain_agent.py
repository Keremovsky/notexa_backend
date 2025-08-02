import json
from typing import AsyncGenerator, Callable, Optional, List
from dotenv import load_dotenv
from models import db_models

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.conversation.base import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.document_loaders import PyPDFLoader


load_dotenv()


def build_memory_from_db(messages: List[dict]) -> ConversationBufferMemory:
    memory = ConversationBufferMemory(return_messages=True)
    for msg in messages:
        if msg["sender"] == "user":
            memory.chat_memory.add_message(HumanMessage(content=msg["text"]))
        elif msg["sender"] == "ai":
            memory.chat_memory.add_message(AIMessage(content=msg["text"]))
    return memory


def initialize_chain(db_chat: db_models.ChatHistory):
    memory = build_memory_from_db(db_chat.messages or [])

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
        streaming=True,
    )

    return ConversationChain(llm=llm, memory=memory, verbose=True), memory
