"""LLM module — OpenAI-compatible API client for all agents."""

from .client import LLMClient, get_llm_client

__all__ = ["LLMClient", "get_llm_client"]
