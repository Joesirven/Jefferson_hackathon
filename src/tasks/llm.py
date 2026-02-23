# src/tasks/llm.py
"""LLM client wrapper for GLM, Gemini, or other providers."""

import os
from typing import Optional, Any
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Base class for LLM clients."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the prompt."""
        pass


class GLMClient(LLMClient):
    """Zhipu GLM client."""

    def __init__(self, api_key: Optional[str] = None):
        import zhipuai
        self.api_key = api_key or os.getenv("ZHIPUAI_API_KEY")
        self.client = zhipuai.ZhipuAI(api_key=self.api_key)
        self.model = "glm-4-flash"  # Cheapest for high volume

    async def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
            **kwargs
        )
        return response.choices[0].message.content


class GeminiClient(LLMClient):
    """Google Gemini client."""

    def __init__(self, api_key: Optional[str] = None):
        import google.generativeai as genai
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")  # Fast/cheap

    async def generate(self, prompt: str, **kwargs) -> str:
        result = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 500,
                **kwargs
            }
        )
        return result.text


class ClaudeClient(LLMClient):
    """Anthropic Claude client (backup option)."""

    def __init__(self, api_key: Optional[str] = None):
        import anthropic
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-haiku-20241022"  # Cheapest Claude

    async def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.content[0].text


def get_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None
) -> LLMClient:
    """
    Get an LLM client instance.

    Args:
        provider: "glm", "gemini", or "claude". Defaults to GLM.
        api_key: Optional API key (otherwise reads from env)
    """
    provider = provider or os.getenv("LLM_PROVIDER", "glm")

    if provider == "glm":
        return GLMClient(api_key)
    elif provider == "gemini":
        return GeminiClient(api_key)
    elif provider == "claude":
        return ClaudeClient(api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")
