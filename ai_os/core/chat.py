import os
import httpx
from typing import List
from .models import Message

def chat_completion(messages: List[Message], model: str = "google/gemini-2.5-flash-preview:thinking", enable_search: bool = False):
    """Sends messages to OpenRouter API and yields response chunks."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")

    client = httpx.Client(
        base_url="https://openrouter.ai/api/v1",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=600.0,
    )

    # Build request payload
    payload = {
        "model": model if not enable_search else f"{model}:online",
        "messages": [msg.model_dump() for msg in messages],
        "stream": True,
    }

    try:
        with client.stream(
            "POST",
            "/chat/completions",
            json=payload,
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_lines():
                if chunk.startswith("data: "):
                    data = chunk.split("data: ")[1]
                    if data == "[DONE]":
                        break
                    import json
                    try:
                        delta = json.loads(data)['choices'][0]['delta']
                        if 'content' in delta:
                            yield delta['content']
                    except json.JSONDecodeError:
                         pass # Ignore malformed data lines
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
    except httpx.RequestError as e:
        print(f"An error occurred while requesting {e.request.url!r}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
