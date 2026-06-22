"""Streaming generators for story creation."""

from __future__ import annotations

import logging
import random
from collections.abc import Iterator

from apps.stories.models import Story
from apps.stories.services import StoryGeneratorService

logger = logging.getLogger(__name__)


def _progress(message: str, percent: int, **extra) -> dict:
    return {"event": "progress", "message": message, "percent": percent, **extra}


def _token(text: str) -> dict:
    return {"event": "token", "text": text}


def _complete(payload: dict) -> dict:
    return {"event": "complete", **payload}


def stream_story_generation(
    *,
    prompt: str,
    language: str,
    genre: str,
    age_group: str,
    story_length: str = "medium",
) -> Iterator[dict]:
    yield _progress("Preparing your story request…", 5)

    if StoryGeneratorService._llm_available():
        try:
            from agents.llm_client import LLMError
            from agents.writer_agent import WriterAgent

            writer = WriterAgent()
            model = writer.client.model
            yield _progress(f"Connecting to {model}…", 12, model=model)
            yield _progress("Llama is writing your story — streaming live…", 18, model=model)

            messages = writer.generate_messages(
                prompt=prompt,
                genre=genre,
                age_group=age_group,
                language=language,
                story_length=story_length,
            )
            parts: list[str] = []
            for token in writer.client.stream_chat(
                messages, temperature=0.85, max_tokens=4096
            ):
                parts.append(token)
                yield _token(token)

            raw = "".join(parts)
            fallback = prompt[:60].title() if prompt else "Untitled Story"
            draft = writer._parse_story_response(raw, fallback)
            _, morals, _, _ = StoryGeneratorService._templates(language)
            moral = draft.moral or random.choice(morals.get(genre, morals["fantasy"]))

            yield _progress("Finalizing story…", 95)
            yield _complete({
                "story": {
                    "title": draft.title,
                    "content": draft.content,
                    "moral": moral,
                    "language": language,
                    "genre": genre,
                    "age_group": age_group,
                    "story_length": story_length,
                    "word_count": draft.word_count,
                    "source": "llama",
                }
            })
            return
        except Exception as exc:
            logger.warning("Streaming story generation failed, using templates: %s", exc)
            yield _progress("Llama unavailable — using demo templates…", 40)

    yield _progress("Building story from templates…", 50)
    story = StoryGeneratorService.generate(
        prompt=prompt,
        language=language,
        genre=genre,
        age_group=age_group,
        story_length=story_length,
    )
    chunk_size = 24
    content = story["content"]
    for index in range(0, len(content), chunk_size):
        piece = content[index : index + chunk_size]
        yield _token(piece)
    yield _progress("Story ready!", 100)
    yield _complete({"story": story})


def stream_story_continue(
    *,
    title: str,
    content: str,
    genre: str,
    age_group: str,
    language: str = Story.Language.ENGLISH,
    story_length: str = "medium",
) -> Iterator[dict]:
    yield _progress("Preparing continuation…", 5)

    if StoryGeneratorService._llm_available():
        try:
            from agents.writer_agent import WriterAgent

            writer = WriterAgent()
            model = writer.client.model
            yield _progress(f"Connecting to {model}…", 15, model=model)
            yield _progress("Continuing your story — streaming live…", 25, model=model)

            messages = writer.continue_messages(
                title=title,
                content=content,
                genre=genre,
                age_group=age_group,
                language=language,
                story_length=story_length,
            )
            parts: list[str] = []
            for token in writer.client.stream_chat(
                messages, temperature=0.85, max_tokens=2048
            ):
                parts.append(token)
                yield _token(token)

            extended = "".join(parts).strip()
            if not extended:
                raise ValueError("Empty continuation from model")

            yield _progress("Continuation complete!", 100)
            yield _complete({"content": f"{content}\n\n{extended}"})
            return
        except Exception as exc:
            logger.warning("Streaming continue failed, using templates: %s", exc)
            yield _progress("Llama unavailable — using demo templates…", 40)

    yield _progress("Extending story from templates…", 55)
    extended = StoryGeneratorService.continue_story(
        title=title,
        content=content,
        genre=genre,
        age_group=age_group,
        language=language,
        story_length=story_length,
    )
    new_part = extended[len(content) :].strip()
    for index in range(0, len(new_part), 24):
        yield _token(new_part[index : index + 24])
    yield _complete({"content": extended})
