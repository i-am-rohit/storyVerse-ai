"""Story writing agent — Llama 3.1 / 3.2 powered story generation."""

import logging
import re
from dataclasses import dataclass

from .llm_client import LLMError, LlamaClient
from .prompts import STORY_CREATOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

LENGTH_GUIDE = {
    "short": "about 150 words",
    "medium": "about 350 words",
    "long": "about 600 words",
    "extra_long": "about 1000 words",
}


@dataclass
class StoryDraft:
    title: str
    content: str
    word_count: int
    moral: str = ""


class WriterAgent:
    """Writes stories using Meta Llama via Ollama or Groq."""

    SYSTEM_PROMPT = STORY_CREATOR_SYSTEM_PROMPT

    def __init__(self, client: LlamaClient | None = None):
        self.client = client or LlamaClient()

    def is_available(self) -> bool:
        return self.client.is_configured()

    @staticmethod
    def _word_count(text: str) -> int:
        return len(re.findall(r"\w+", text))

    @staticmethod
    def _parse_story_response(raw: str, fallback_title: str) -> StoryDraft:
        text = raw.strip()
        moral = ""

        moral_match = re.search(
            r"(?:^|\n)\s*(?:Moral|Lesson)\s*:\s*(.+)$",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if moral_match:
            moral = moral_match.group(1).strip()
            text = text[: moral_match.start()].strip()

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        title = fallback_title
        content_lines = lines

        if lines:
            first = lines[0]
            if len(first) < 120 and not first.endswith("."):
                title = first.lstrip("#").strip().strip('"')
                content_lines = lines[1:]

        content = "\n\n".join(content_lines).strip() or text
        return StoryDraft(
            title=title,
            content=content,
            word_count=WriterAgent._word_count(content),
            moral=moral,
        )

    def _build_generate_user_prompt(
        self,
        *,
        prompt: str,
        genre: str,
        age_group: str,
        language: str = "en",
        story_length: str = "medium",
    ) -> str:
        length_label = LENGTH_GUIDE.get(story_length, LENGTH_GUIDE["medium"])
        lang_label = "Hindi" if language == "hi" else "English"
        return (
            f"Write a {length_label} {genre.replace('_', ' ')} story in {lang_label}.\n"
            f"Target audience: ages {age_group}.\n"
            f"Story idea: {prompt}\n\n"
            "Rules:\n"
            "- Write engaging narrative with dialogue, vivid scenes, and a clear ending.\n"
            "- Put the story title on the very first line (no markdown headings).\n"
            "- Write the full story below the title as plain paragraphs.\n"
            "- End with a line: Moral: <one sentence lesson>.\n"
            "- Do not include labels like 'Title:' or 'Story:'."
        )

    def _build_continue_user_prompt(
        self,
        *,
        title: str,
        content: str,
        genre: str,
        age_group: str,
        language: str = "en",
        story_length: str = "medium",
    ) -> str:
        length_label = LENGTH_GUIDE.get(story_length, LENGTH_GUIDE["medium"])
        lang_label = "Hindi" if language == "hi" else "English"
        return (
            f"Continue this {genre.replace('_', ' ')} story in {lang_label}.\n"
            f"Add {length_label} of new content.\n"
            f"Target audience: ages {age_group}.\n"
            f"Title: {title}\n\n"
            f"Story so far:\n{content[-6000:]}\n\n"
            "Write only the continuation — plain paragraphs, no headings or metadata."
        )

    def generate_messages(
        self,
        *,
        prompt: str,
        genre: str,
        age_group: str,
        language: str = "en",
        story_length: str = "medium",
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": self._build_generate_user_prompt(
                    prompt=prompt,
                    genre=genre,
                    age_group=age_group,
                    language=language,
                    story_length=story_length,
                ),
            },
        ]

    def continue_messages(
        self,
        *,
        title: str,
        content: str,
        genre: str,
        age_group: str,
        language: str = "en",
        story_length: str = "medium",
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": self._build_continue_user_prompt(
                    title=title,
                    content=content,
                    genre=genre,
                    age_group=age_group,
                    language=language,
                    story_length=story_length,
                ),
            },
        ]

    def generate_story(
        self,
        *,
        prompt: str,
        genre: str,
        age_group: str,
        language: str = "en",
        story_length: str = "medium",
    ) -> StoryDraft:
        raw = self.client.complete(
            self.SYSTEM_PROMPT,
            self._build_generate_user_prompt(
                prompt=prompt,
                genre=genre,
                age_group=age_group,
                language=language,
                story_length=story_length,
            ),
            temperature=0.85,
            max_tokens=4096,
        )
        fallback = prompt[:60].title() if prompt else "Untitled Story"
        return self._parse_story_response(raw, fallback)

    def continue_story(
        self,
        *,
        title: str,
        content: str,
        genre: str,
        age_group: str,
        language: str = "en",
        story_length: str = "medium",
    ) -> str:
        return self.client.complete(
            self.SYSTEM_PROMPT,
            self._build_continue_user_prompt(
                title=title,
                content=content,
                genre=genre,
                age_group=age_group,
                language=language,
                story_length=story_length,
            ),
            temperature=0.85,
            max_tokens=2048,
        )

    def write(self, outline: list[str], style: str = "narrative") -> StoryDraft:
        prompt = " ".join(outline) if outline else "An original adventure"
        return self.generate_story(
            prompt=prompt,
            genre="fantasy",
            age_group="6-8",
            story_length="medium",
        )
