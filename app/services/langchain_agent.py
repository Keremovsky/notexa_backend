import json
from typing import AsyncGenerator, Callable, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# from langchain_core.messages import HumanMessage

load_dotenv()


# TODO: implement langchain and gemini api call
async def stream_chat_response_json(
    prompt: str,
    on_token: Optional[Callable[[str], None]] = None,
) -> AsyncGenerator[str, None]:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
    )

    async for chunk in llm.astream(prompt):
        token = chunk.content
        if on_token:
            on_token(token)
        chunk = json.dumps({"sender": "ai", "answer": token})
        yield f"data: {chunk}\n\n"

    yield f"data: {json.dumps({'sender': 'ai', 'answer': '[END]'})}\n\n"
