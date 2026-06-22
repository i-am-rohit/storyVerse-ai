"""Llama 3.1 / 3.2 client — Ollama (local) or Groq (free API)."""

import json
import logging
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 180


class LLMError(Exception):
    """Raised when the Llama model cannot complete a request."""


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


class LlamaClient:
    """Chat completions via Meta Llama models (Ollama local or Groq API)."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.provider = (provider or settings.LLM_PROVIDER).lower().strip()
        self.model = model or settings.LLAMA_MODEL
        self.api_key = api_key or getattr(settings, "GROQ_API_KEY", "")
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    def is_configured(self) -> bool:
        if not settings.LLM_ENABLED:
            return False
        if self.provider == "groq":
            return bool(self.api_key)
        if self.provider == "ollama":
            return True
        return False

    def _chat_url(self) -> str:
        if self.provider == "groq":
            return "https://api.groq.com/openai/v1/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.provider == "groq":
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> LLMResponse:
        if not self.is_configured():
            raise LLMError(
                "Llama LLM is not configured. Set LLM_ENABLED=true and use "
                "LLM_PROVIDER=ollama (local) or LLM_PROVIDER=groq with GROQ_API_KEY."
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self._chat_url(),
            data=data,
            headers=self._headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=timeout, context=_ssl_context()
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise LLMError(f"Llama API error ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            if self.provider == "ollama":
                raise LLMError(
                    "Cannot reach Ollama. Start it with: ollama serve "
                    f"and pull the model: ollama pull {self.model}"
                ) from exc
            raise LLMError(f"Llama API connection failed: {exc}") from exc

        try:
            content = body["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected Llama API response: {body}") from exc

        return LLMResponse(content=content, model=self.model, provider=self.provider)

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """Yield text tokens from a streaming chat completion."""
        if not self.is_configured():
            raise LLMError(
                "Llama LLM is not configured. Set LLM_ENABLED=true and use "
                "LLM_PROVIDER=ollama (local) or LLM_PROVIDER=groq with GROQ_API_KEY."
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self._chat_url(),
            data=data,
            headers=self._headers(),
            method="POST",
        )

        try:
            response = urllib.request.urlopen(
                request, timeout=timeout, context=_ssl_context()
            )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise LLMError(f"Llama API error ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            if self.provider == "ollama":
                raise LLMError(
                    "Cannot reach Ollama. Start it with: ollama serve "
                    f"and pull the model: ollama pull {self.model}"
                ) from exc
            raise LLMError(f"Llama API connection failed: {exc}") from exc

        try:
            while True:
                raw_line = response.readline()
                if not raw_line:
                    break
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                text = delta.get("content") or ""
                if text:
                    yield text
        finally:
            response.close()

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages, **kwargs).content
