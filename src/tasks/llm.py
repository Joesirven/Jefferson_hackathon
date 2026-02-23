# src/tasks/llm.py (CORRECTED VERSION)
"""LLM client wrapper for GLM, Gemini, or other providers."""

from dotenv import load_dotenv
from zai import ZaiClient
from zai.models import Model

# Load environment variables from .env file
load_dotenv()

import os
from abc import ABC, abstractmethod
from typing import Any, Optional


class LLMClient(ABC):
    """Base class for LLM clients."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the prompt."""
        pass

        from dotenv import load_dotenv
        from zai.models import Model

        # Load environment variables from .env file
        load_dotenv()

        self.api_key = api_key or os.getenv("ZHIPUAI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "ZHIPUAI_API_KEY must be set in environment. "
                "Get it from your Z.AI project settings."
            )

        # Initialize Z.AI client
        self.client = ZaiClient(api_key=self.api_key)

        # Initialize Z.AI client
        self.client = ZaiClient(api_key=self.api_key)

        self.coding_endpoint = True  # Using dedicated coding endpoint


class GeminiClient(LLMClient):
    """Google Gemini client."""

    def __init__(self, api_key: Optional[str] = None):
        from dotenv import load_dotenv

        # Load environment variables
        load_dotenv()

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def generate(self, prompt: str, **kwargs) -> str:
        try:
            result = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_output_tokens": kwargs.get("max_tokens", 500),
                    **kwargs,
                },
            )
            return result.text
        except Exception as e:
            raise RuntimeError(f"Error generating response: {e}")


class ClaudeClient(LLMClient):
    """Anthropic Claude client (backup option)."""

    def __init__(self, api_key: Optional[str] = None):
        from dotenv import load_dotenv

        # Load environment variables
        load_dotenv()

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-haiku-20241022"

    async def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 500),
                temperature=kwargs.get("temperature", 0.7),
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Error generating response: {e}")


def get_llm_client(
    provider: Optional[str] = None, api_key: Optional[str] = None
) -> LLMClient:
    """
    Get an LLM client instance.

    Args:
        provider: "glm", "gemini", or "claude". Defaults to GLM.
        api_key: Optional API key (otherwise reads from env)
    """
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    provider = provider or os.getenv("LLM_PROVIDER", "glm")

    if provider == "glm":
        return GLMClient(api_key)
    elif provider == "gemini":
        return GeminiClient(api_key)
    elif provider == "claude":
        return ClaudeClient(api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")
