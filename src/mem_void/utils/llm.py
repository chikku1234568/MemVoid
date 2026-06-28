from __future__ import annotations

from mem_void.config import Settings


def _get_client(settings: Settings):
    """Return an OpenAI-compatible client based on settings."""
    from openai import OpenAI

    if settings.llm_provider == "ollama" and settings.llm_base_url:
        return OpenAI(base_url=settings.llm_base_url, api_key="ollama")

    return OpenAI(api_key=settings.llm_api_key)


def generate(settings: Settings, prompt: str) -> str:
    """Send a prompt to the configured LLM and return the response text."""
    client = _get_client(settings)
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return response.choices[0].message.content or ""
