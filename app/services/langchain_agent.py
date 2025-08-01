import asyncio
import json
from typing import AsyncGenerator, Callable, Optional


# TODO: implement langchain and gemini api call
async def stream_chat_response_json(
    prompt: str,
    on_token: Optional[Callable[[str], None]] = None,
) -> AsyncGenerator[str, None]:
    dummy_response = (
        f"You asked: {prompt}. Here's a simulated AI reply streamed in chunks..."
    )
    tokens = dummy_response.split()

    for token in tokens:
        if on_token:
            on_token(token)
        chunk = json.dumps({"sender": "ai", "answer": token})
        yield f"data: {chunk}\n\n"
        await asyncio.sleep(0.1)

    yield f"data: {json.dumps({'sender': 'ai', 'answer': '[END]'})}\n\n"
