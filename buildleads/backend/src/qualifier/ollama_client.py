"""Ollama API wrapper with chat API support.

Supports both /api/generate and /api/chat endpoints.
"""

import httpx

from src.config import settings

TIMEOUT = httpx.Timeout(120.0, connect=10.0)


async def generate(prompt: str, model: str = "gemma2:9b") -> str:
    """Send a prompt to Ollama and return the response text."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{settings.ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return resp.json().get("response", "")


async def chat(messages: list[dict], model: str = "gemma2:9b") -> str:
    """Send chat messages to Ollama and return assistant response."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{settings.ollama_url}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")


async def is_available() -> bool:
    """Check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
