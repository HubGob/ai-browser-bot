"""LLM client abstraction — pluggable chat completion interface."""

from __future__ import annotations

from typing import Any

import httpx


class LLMClient:
    """Abstract interface for chat-completion LLMs.

    Subclass or configure with an http_client + base_url to support
    any OpenAI-compatible API.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._http = http_client or httpx.AsyncClient(timeout=30.0)

    async def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a chat request and return the parsed response.

        Returns:
            {"role": "assistant", "content": "...", ...} or
            {"error": "..."} on failure.
        """
        raise NotImplementedError

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()


class OpenAICompatibleClient(LLMClient):
    """Client for any OpenAI-compatible API (OpenAI, Azure, LM Studio, etc.)."""

    async def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }

        try:
            resp = await self._http.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            return {
                "role": choice["message"]["role"],
                "content": choice["message"]["content"],
                "model": data.get("model"),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:  # noqa: BLE001 — all LLM errors are captured as structured results
            return {"error": str(e)}
