"""NexaAI provider — local OpenAI-compatible API with NexaSDK-specific handling."""

from __future__ import annotations

import uuid
from typing import Any

import json_repair
from openai import AsyncOpenAI

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class NexaaiProvider(LLMProvider):
    """NexaAI provider for local NexaSDK inference.

    NexaSDK provides OpenAI-compatible API but has some specific limitations:
    - Context length is more strictly enforced
    - Some parameters may not be fully supported
    - Error handling differs from standard OpenAI API
    """

    def __init__(self, api_key: str = "no-key", api_base: str = "http://127.0.0.1:18181/v1", default_model: str = "default"):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        # Keep affinity stable for this provider instance to improve backend cache locality.
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
            default_headers={"x-session-affinity": uuid.uuid4().hex},
        )

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
                   model: str | None = None, max_tokens: int = 4096, temperature: float = 0.7,
                   reasoning_effort: str | None = None) -> LLMResponse:
        """Send chat completion request to NexaAI.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions.
            model: Model identifier.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
            reasoning_effort: Reasoning effort (not supported by NexaSDK, ignored).

        Returns:
            LLMResponse with content and/or tool calls.
        """
        # NexaSDK has stricter context limits, use conservative defaults
        # and avoid sending too many messages at once
        sanitized_messages = self._sanitize_empty_content(messages)

        # Build kwargs with only supported parameters
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": sanitized_messages,
            "max_tokens": max(1, min(max_tokens, 2048)),  # NexaSDK may have lower limits
            "temperature": temperature,
        }

        # NexaSDK may not support reasoning_effort, skip it
        # if reasoning_effort:
        #     kwargs["reasoning_effort"] = reasoning_effort

        if tools:
            kwargs.update(tools=tools, tool_choice="auto")

        try:
            return self._parse(await self._client.chat.completions.create(**kwargs))
        except Exception as e:
            error_msg = str(e)
            # Handle specific NexaSDK errors
            if "Context length exceeded" in error_msg or "-200004" in error_msg:
                # Try with truncated messages
                truncated_messages = self._truncate_messages(sanitized_messages)
                kwargs["messages"] = truncated_messages
                try:
                    return self._parse(await self._client.chat.completions.create(**kwargs))
                except Exception as e2:
                    return LLMResponse(content=f"Error: Context length exceeded even after truncation. {e2}", finish_reason="error")
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    def _truncate_messages(self, messages: list[dict[str, Any]], max_messages: int = 10) -> list[dict[str, Any]]:
        """Truncate message history to fit within context limits.

        Keeps system message and most recent messages.

        Args:
            messages: Original message list.
            max_messages: Maximum number of messages to keep.

        Returns:
            Truncated message list.
        """
        if len(messages) <= max_messages:
            return messages

        # Keep system message if present
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        # Keep most recent messages
        kept_other = other_msgs[-(max_messages - len(system_msgs)):]

        return system_msgs + kept_other

    def _parse(self, response: Any) -> LLMResponse:
        """Parse OpenAI-compatible response into LLMResponse.

        Args:
            response: Raw API response.

        Returns:
            Parsed LLMResponse.
        """
        choice = response.choices[0]
        msg = choice.message
        tool_calls = [
            ToolCallRequest(id=tc.id, name=tc.function.name,
                            arguments=json_repair.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments)
            for tc in (msg.tool_calls or [])
        ]
        u = response.usage
        return LLMResponse(
            content=msg.content, tool_calls=tool_calls, finish_reason=choice.finish_reason or "stop",
            usage={"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens, "total_tokens": u.total_tokens} if u else {},
            reasoning_content=getattr(msg, "reasoning_content", None) or None,
        )

    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        return self.default_model
