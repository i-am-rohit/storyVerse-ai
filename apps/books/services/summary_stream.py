"""Streaming generators for book summarization."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from .summary_service import SummaryService

logger = logging.getLogger(__name__)

ALL_STEPS = [
    ("short", "Short summary", "short_summary", 8),
    ("full_book", "Full book summary", "detailed_summary", 20),
    ("main_points", "Main points", "main_points", 35),
    ("chapters_short", "Chapter-wise summaries", "chapter_short_summaries", 50),
    ("chapters", "Chapter summaries", "chapter_summaries", 68),
    ("short_stories", "Short stories", "short_stories", 82),
    ("reading_guide", "Reading guide", "reading_guide", 92),
]

TYPE_STEPS = {
    "short": [("short", "Short summary", "short_summary", 15)],
    "detailed": [("full_book", "Full book summary", "detailed_summary", 15)],
    "full_book": [("full_book", "Full book summary", "detailed_summary", 15)],
    "main_points": [("main_points", "Main points", "main_points", 15)],
    "chapters_short": [("chapters_short", "Chapter-wise summaries", "chapter_short_summaries", 15)],
    "chapters": [("chapters", "Chapter summaries", "chapter_summaries", 15)],
    "short_stories": [("short_stories", "Short stories", "short_stories", 15)],
    "reading_guide": [("reading_guide", "Reading guide", "reading_guide", 15)],
    "all": ALL_STEPS,
}


def _progress(message: str, percent: int, **extra) -> dict:
    return {"event": "progress", "message": message, "percent": percent, **extra}


def _token(text: str, target: str = "") -> dict:
    payload = {"event": "token", "text": text}
    if target:
        payload["target"] = target
    return payload


def _complete(generated: dict) -> dict:
    return {"event": "complete", "generated": generated}


def _stream_llm_text(
  agent,
  text: str,
  title: str,
  *,
  style: str,
  target: str,
  max_words: int = 0,
  max_tokens: int = 2048,
) -> Iterator[dict]:
    parts: list[str] = []
    for token in agent.stream_summarize_text(
        text, title, style=style, max_words=max_words, max_tokens=max_tokens
    ):
        parts.append(token)
        yield _token(token, target=target)
    return "".join(parts).strip()


def _run_step(
    step_key: str,
    label: str,
    field: str,
    base_percent: int,
    text: str,
    title: str,
    page_count: int,
    agent,
    llm_available: bool,
) -> Iterator[dict | str]:
    yield _progress(f"{label}…", base_percent, step=step_key, target=field)

    if step_key in ("short", "full_book"):
        narrative = SummaryService._prepare_narrative(text)
        if not narrative:
            yield SummaryService.INSUFFICIENT_MESSAGE if step_key == "short" else ""
            return

        if llm_available:
            style = "short" if step_key == "short" else "full"
            yield _progress(
                f"Llama is writing {label.lower()} — streaming live…",
                min(base_percent + 4, 98),
                step=step_key,
                target=field,
            )
            parts: list[str] = []
            for token in agent.stream_summarize_text(
                narrative, title, style=style, max_tokens=3072 if style == "full" else 1024
            ):
                parts.append(token)
                yield _token(token, target=field)
            yield "".join(parts).strip()
            return

        if step_key == "short":
            yield SummaryService.generate_short(text, title)
        else:
            yield SummaryService.generate_full_book(text, title)
        return

    if step_key == "main_points":
        yield SummaryService.generate_main_points(text, title)
        return
    if step_key == "chapters_short":
        yield _progress("Detecting chapters in your book…", base_percent + 2, step=step_key)
        yield SummaryService.generate_chapters_short(text)
        return
    if step_key == "chapters":
        yield _progress("Detecting chapters in your book…", base_percent + 2, step=step_key)
        if llm_available:
            chapters = SummaryService._split_chapters(text)
            results = []
            total = min(len(chapters), 15)
            for index, (chapter_title, body) in enumerate(chapters[:15], start=1):
                if SummaryService._word_count(body) < 30:
                    continue
                yield _progress(
                    f"Summarizing chapter {index}/{total}: {chapter_title[:60]}…",
                    min(base_percent + int(20 * index / max(total, 1)), 97),
                    step=step_key,
                    chapter=index,
                    total=total,
                    chapter_title=chapter_title,
                )
                parts: list[str] = []
                for token in agent.stream_summarize_text(
                    body, title, style="chapter", max_tokens=512
                ):
                    parts.append(token)
                    yield _token(token, target=field)
                summary_text = "".join(parts).strip()
                if summary_text:
                    results.append({
                        "title": chapter_title,
                        "summary": summary_text,
                        "word_count": SummaryService._word_count(body),
                    })
            yield results
            return
        yield SummaryService.generate_chapters(text)
        return
    if step_key == "short_stories":
        yield SummaryService.generate_short_stories(text, title)
        return
    if step_key == "reading_guide":
        yield SummaryService.generate_reading_guide(text, title, page_count)
        return

    yield None


def stream_summary_generation(
    summary_type: str,
    text: str,
    title: str,
    page_count: int = 0,
) -> Iterator[dict]:
    steps = TYPE_STEPS.get(summary_type, TYPE_STEPS["all"])
    agent = SummaryService._summary_agent()
    llm_available = SummaryService._llm_available()
    model = agent.client.model if llm_available else ""

    yield _progress("Reading and cleaning your document…", 3)
    if llm_available:
        yield _progress(f"Connected to {model}", 8, model=model)
    else:
        yield _progress("Using local analysis (Llama offline)", 8)

    generated: dict = {}
    for step_key, label, field, base_percent in steps:
        result = None
        for item in _run_step(
            step_key,
            label,
            field,
            base_percent,
            text,
            title,
            page_count,
            agent,
            llm_available,
        ):
            if isinstance(item, dict):
                yield item
            else:
                result = item

        if result is not None:
            generated[field] = result
            yield _progress(f"{label} complete", min(base_percent + 6, 99), step=step_key, target=field)

    yield _progress("All summaries ready!", 100)
    yield _complete(generated)
