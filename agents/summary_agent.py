"""Summary agent — Llama 3.1 / 3.2 powered book summarization."""

import logging
import re
from dataclasses import dataclass

from .llm_client import LLMError, LlamaClient
from .prompts import BOOK_SUMMARIZER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 12_000


@dataclass
class Summary:
    text: str
    word_count: int


class SummaryAgent:
    """Summarizes books and documents using Meta Llama via Ollama or Groq."""

    SYSTEM_PROMPT = BOOK_SUMMARIZER_SYSTEM_PROMPT

    def __init__(self, client: LlamaClient | None = None):
        self.client = client or LlamaClient()

    def is_available(self) -> bool:
        return self.client.is_configured()

    @staticmethod
    def _word_count(text: str) -> int:
        return len(re.findall(r"\w+", text))

    @staticmethod
    def _trim_text(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rsplit(" ", 1)[0] + "…"

    def _complete(self, user_prompt: str, *, max_tokens: int = 2048) -> str:
        return self.client.complete(
            self.SYSTEM_PROMPT,
            user_prompt,
            temperature=0.4,
            max_tokens=max_tokens,
        )

    def _build_user_prompt(
        self,
        text: str,
        title: str = "",
        *,
        style: str = "short",
        max_words: int = 0,
    ) -> str:
        chunk = self._trim_text(text, MAX_CHUNK_CHARS)
        title_line = f'Book title: "{title}"\n' if title else ""

        if style == "short":
            instruction = (
                "Write a short story summary in 3-5 sentences. "
                "Plain prose only — no headings, bullets, or metadata."
            )
        elif style == "full":
            instruction = (
                "Write a full story summary in 4-8 paragraphs. "
                "Tell what happens in the plot from beginning to end. "
                "Plain prose only — no headings, bullets, or metadata. "
                "Ready to be read aloud as an audiobook."
            )
        elif style == "chapter":
            instruction = (
                "Summarize this chapter/section in 2-4 sentences. "
                "Plain prose only — no headings."
            )
        elif style == "short_story":
            instruction = (
                "Turn this section into a short standalone story (about 120-180 words). "
                "Plain prose only — no headings."
            )
        else:
            instruction = "Summarize the story content in plain prose."

        if max_words:
            instruction += f" Keep it under {max_words} words."

        return (
            f"{title_line}{instruction}\n\n"
            f"Source text:\n{chunk}"
        )

    def stream_summarize_text(
        self,
        text: str,
        title: str = "",
        *,
        style: str = "short",
        max_words: int = 0,
        max_tokens: int = 2048,
    ):
        user_prompt = self._build_user_prompt(
            text, title, style=style, max_words=max_words
        )
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        yield from self.client.stream_chat(
            messages,
            temperature=0.4,
            max_tokens=max_tokens,
        )

    def summarize_text(
        self,
        text: str,
        title: str = "",
        *,
        style: str = "short",
        max_words: int = 0,
    ) -> Summary:
        user_prompt = self._build_user_prompt(
            text, title, style=style, max_words=max_words
        )

        result = self._complete(user_prompt)
        return Summary(text=result.strip(), word_count=self._word_count(result))

    def summarize_chapters(
        self,
        chapters: list[tuple[str, str]],
        title: str = "",
        *,
        short: bool = False,
        max_chapters: int = 15,
    ) -> list[dict]:
        results = []
        for label, body in chapters[:max_chapters]:
            body_chunk = self._trim_text(body, MAX_CHUNK_CHARS)
            if self._word_count(body_chunk) < 30:
                continue
            try:
                summary = self.summarize_text(
                    body_chunk,
                    title,
                    style="chapter" if not short else "short",
                )
                results.append({
                    "title": label,
                    "summary": summary.text,
                    "word_count": self._word_count(body_chunk),
                })
            except LLMError as exc:
                logger.warning("Chapter summary failed for %s: %s", label, exc)
                continue

        return results

    def summarize_short_stories(
        self,
        chapters: list[tuple[str, str]],
        title: str = "",
        max_chapters: int = 8,
    ) -> list[dict]:
        results = []
        for label, body in chapters[:max_chapters]:
            body_chunk = self._trim_text(body, MAX_CHUNK_CHARS)
            if self._word_count(body_chunk) < 50:
                continue
            try:
                summary = self.summarize_text(body_chunk, title, style="short_story")
                results.append({
                    "title": label,
                    "content": summary.text,
                    "moral": "",
                    "source_chapter": label,
                    "word_count": summary.word_count,
                })
            except LLMError as exc:
                logger.warning("Short story failed for %s: %s", label, exc)
                continue
        return results

    def summarize(self, content: str, max_words: int = 150) -> Summary:
        return self.summarize_text(content, style="short", max_words=max_words)
