import asyncio
import json
from typing import AsyncGenerator


# TODO: implement langchain and gemini api call
async def stream_chat_response_json(prompt: str) -> AsyncGenerator[str, None]:
    dummy_response = (
        f"You asked: {prompt}. Here's a simulated AI reply streamed in chunks..."
    )
    tokens = dummy_response.split()

    for token in tokens:
        chunk = json.dumps({"sender": "ai", "answer": token})
        yield f"data: {chunk}\n\n"
        await asyncio.sleep(0.1)

    # Send an explicit end message if you want (optional)
    yield f"data: {json.dumps({'sender': 'ai', 'answer': '[END]'})}\n\n"
