"""
LLM Client — OpenAI-compatible API wrapper.

Supports any provider that implements the OpenAI chat/completions API:
- OpenAI (gpt-4o, gpt-4, gpt-3.5-turbo)
- DeepSeek (deepseek-chat, deepseek-reasoner)
- Moonshot / Kimi (moonshot-v1-8k)
- Alibaba Qwen (qwen-max, qwen-plus)
- Zhipu GLM (glm-4)
- Local models via vLLM / Ollama

Configuration via .env:
    OPENAI_API_KEY=sk-xxx          # Required
    OPENAI_BASE_URL=https://...    # Optional, defaults to OpenAI
    LLM_MODEL=gpt-4o               # Model name
    LLM_TEMPERATURE=0.1            # 0-2, lower = more deterministic
    LLM_MAX_TOKENS=4096            # Max output tokens
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from ..utils.config import get_settings
from ..utils.logger import get_logger

# Lazy import — system works without openai installed (fallback mode)
_AsyncOpenAI = None


def _get_async_openai():
    """Lazy-load AsyncOpenAI. Raises clear error if not installed."""
    global _AsyncOpenAI
    if _AsyncOpenAI is not None:
        return _AsyncOpenAI
    try:
        from openai import AsyncOpenAI as _AsyncOpenAI_Cls
        _AsyncOpenAI = _AsyncOpenAI_Cls
        return _AsyncOpenAI
    except ImportError:
        raise ImportError(
            "openai package is not installed. Install with: pip install openai\n"
            "Or run without LLM (system will use fallback rule-based mode)."
        )

logger = get_logger(__name__)


class LLMClient:
    """Async OpenAI-compatible LLM client used by all 6 agents.

    Usage::

        client = LLMClient()
        response = await client.chat([
            {"role": "system", "content": "You are a research planner."},
            {"role": "user", "content": "Analyze the battery industry."},
        ])
        # response = "I'll break this down into..."

        # With structured JSON output:
        result = await client.chat_json([
            {"role": "user", "content": "Classify: 'analyze battery market'"}
        ], schema={"type": "object", "properties": {"type": {"type": "string"}}})
        # result = {"type": "industry_analysis"}
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.model: str = settings.LLM_MODEL
        self.temperature: float = settings.LLM_TEMPERATURE
        self.max_tokens: int = settings.LLM_MAX_TOKENS
        self._api_key: str = settings.OPENAI_API_KEY
        self._base_url: str = settings.OPENAI_BASE_URL or ""

        # Validate API key
        self._available: bool = bool(self._api_key and self._api_key not in (
            "sk-your-api-key-here", "sk-your-openai-api-key",
            "sk-your-deepseek-key", "sk-your-qwen-key",
            "sk-your-moonshot-key", "your-zhipu-key", "not-needed",
        ))

        if self._available:
            try:
                AsyncOpenAI = _get_async_openai()
                kwargs: dict = {
                    "api_key": self._api_key,
                    "timeout": 120.0,
                    "max_retries": 2,
                }
                if self._base_url:
                    kwargs["base_url"] = self._base_url
                self._client = AsyncOpenAI(**kwargs)
                logger.info(f"[LLM] Initialized: model={self.model}, base_url={self._base_url or 'OpenAI default'}")
            except ImportError as e:
                self._available = False
                logger.warning(f"[LLM] openai not installed, running in fallback mode: {e}")
            except Exception as e:
                self._available = False
                logger.warning(f"[LLM] Init failed, running in fallback mode: {e}")
        else:
            logger.warning(
                f"[LLM] No valid API key found (current: {self._api_key[:20]}...). "
                "All agents will use rule-based fallback. "
                "Set OPENAI_API_KEY in .env to enable LLM reasoning."
            )

    # ── Core API ──────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Check if the LLM client is ready for API calls."""
        return self._available

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> str:
        """Send a chat completion request and return the text response.

        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            temperature: Override default temperature (0-2).
            max_tokens: Override default max output tokens.
            stop: Optional stop sequences.

        Returns:
            The model's text response.

        Raises:
            RuntimeError: If the API call fails after all retries.
        """
        start_time = time.time()

        if not self._available:
            raise RuntimeError("LLM client is not available (no valid API key configured)")
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stop=stop,
            )
            elapsed = time.time() - start_time
            content = response.choices[0].message.content or ""
            usage = response.usage
            logger.info(
                f"[LLM] chat: model={self.model}, "
                f"tokens_in={usage.prompt_tokens if usage else '?'}, "
                f"tokens_out={usage.completion_tokens if usage else '?'}, "
                f"time={elapsed:.1f}s, "
                f"len={len(content)}"
            )
            return content

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[LLM] chat failed after {elapsed:.1f}s: {e}")
            raise RuntimeError(f"LLM API call failed: {e}") from e

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: dict | None = None,
        temperature: float | None = None,
    ) -> dict:
        """Send a chat request and parse the response as JSON.

        Uses two strategies:
        1. If schema is provided, adds a system instruction to return JSON
        2. Tries to extract JSON from the response text

        Args:
            messages: Chat messages.
            schema: Optional JSON Schema for the expected output shape.
            temperature: Override temperature (uses lower default for JSON).

        Returns:
            Parsed JSON dict. Returns {"raw": "...", "_parse_error": True} on failure.
        """
        # Add JSON instruction
        json_messages = list(messages)
        schema_instruction = (
            "\n\nIMPORTANT: You MUST respond with ONLY valid JSON. "
            "Do not include markdown code blocks, explanations, or any other text. "
            "Output raw JSON only."
        )
        if schema:
            schema_instruction += f"\n\nExpected JSON schema:\n```json\n{json.dumps(schema, indent=2)}\n```"

        # Add to the last message or as a system message
        if json_messages and json_messages[-1]["role"] == "user":
            json_messages[-1]["content"] += schema_instruction
        else:
            json_messages.append({"role": "system", "content": schema_instruction.strip()})

        # Use lower temperature for structured output
        json_temp = temperature if temperature is not None else min(self.temperature, 0.3)

        text = await self.chat(json_messages, temperature=json_temp)

        # Try to parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding first { } block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"[LLM] chat_json: failed to parse JSON from response: {text[:200]}")
        return {"raw": text, "_parse_error": True}


# ── Global singleton ──────────────────────────────────────────────────────

_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
