"""Ollama API wrapper — for future AI-powered lead qualification.

Will be used in Phase 3 for:
- Lead scoring enhancement (1-10 scale)
- Material category classification
- AI summary generation
- Contact data enrichment
"""

import httpx

from src.config import settings

TIMEOUT = httpx.Timeout(60.0, connect=10.0)


async def generate(prompt: str, model: str = "llama3.2:3b") -> str:
    """Send a prompt to Ollama and return the response text."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{settings.ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return resp.json().get("response", "")


async def is_available() -> bool:
    """Check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
