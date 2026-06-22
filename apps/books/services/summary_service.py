import logging
import re
import textwrap

from agents.prompts import BOOK_SUMMARIZER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MIN_STORY_WORDS = 80

BOILERPLATE_LINE_PATTERNS = [
    re.compile(r"project gutenberg", re.I),
    re.compile(r"^\s*copyright\b", re.I),
    re.compile(r"all rights reserved", re.I),
    re.compile(r"^\s*distributed proofreading", re.I),
    re.compile(r"^\s*table of contents\s*$", re.I),
    re.compile(r"^\s*contents\s*$", re.I),
    re.compile(r"^\s*acknowledg(e)?ments?\s*$", re.I),
    re.compile(r"^\s*license\b", re.I),
    re.compile(r"^\s*isbn\b", re.I),
    re.compile(r"^\s*published by\b", re.I),
    re.compile(r"^\s*translated by\b", re.I),
    re.compile(r"^\s*editor(?:ial)?\b", re.I),
    re.compile(r"^\s*preface\s*$", re.I),
    re.compile(r"^\s*page\s+\d+\s*$", re.I),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"\.{5,}"),  # table of contents dot leaders
    re.compile(r"pictures for\b", re.I),
    re.compile(r"formatted from\b", re.I),
    re.compile(r"electronic form\b", re.I),
    re.compile(r"without any warranty", re.I),
    re.compile(r"merchantab", re.I),
    re.compile(r"fitness for a particular purpose", re.I),
]

JUNK_SENTENCE_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"warranty",
        r"gutenberg",
        r"copyright",
        r"as-is",
        r"as is",
        r"merchantab",
        r"fitness for a particular purpose",
        r"expressed or implied",
        r"pictures for",
        r"formatted from",
        r"electronic form",
        r"table of contents",
        r"http[s]?://",
        r"www\.",
        r"edition of",
        r"smith, elder",
        r"version \d+\.\d+",
        r"collection's version",
        r"\.{4,}",
        r"^\s*preface\b",
        r"additional information about",
        r"provided to you",
        r"free ascii",
        r"html variants",
    ]
]

NAME_STOP_WORDS = {
    "The", "This", "That", "They", "There", "Then", "When", "What", "Where",
    "Which", "While", "With", "Would", "Could", "Should", "From", "Into",
    "Upon", "After", "Before", "About", "Above", "Below", "Under", "Over",
    "Chapter", "Part", "Section", "Book", "Volume", "You", "But", "And",
    "Yes", "She", "He", "His", "Her", "Him", "They", "Them", "Well", "Now",
    "Then", "However", "Perhaps", "Surely", "Indeed", "Why", "How", "Oh",
    "Ah", "Here", "These", "Those", "Shall", "Will", "May", "Might", "Must",
    "Not", "Nor", "For", "Yet", "Still", "Even", "Only", "Just", "Very",
    "Much", "More", "Most", "Some", "Any", "All", "Both", "Each", "Every",
    "Such", "Same", "Other", "Another", "One", "Two", "First", "Last", "Next",
    "Great", "Little", "Good", "New", "Old", "Young", "Being", "Having",
    "Though", "Although", "Unless", "Until", "Since", "Because", "Whether",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December", "God", "Lord", "Sir",
    "Lady", "King", "Queen", "Prince", "Princess", "Captain", "General",
    "Colonel", "Professor", "Doctor", "Mr", "Mrs", "Miss", "Ms", "Dr",
    "London", "England", "India", "America", "Street", "Road", "House", "Room",
    "Holmes",  # allow only as part of full name via titled names
}

STORY_START_PATTERNS = [
    re.compile(r"CHAPTER\s+[IVXLC\d]+[\.:\s]", re.I),
    re.compile(r"Chapter\s+[IVXLC\d]+[\.:\s]", re.I),
    re.compile(r"ADVENTURE\s+OF\s+THE\b", re.I),
    re.compile(r"The Adventure of\b", re.I),
]


class SummaryService:
    """Generates book summaries via Llama 3.1/3.2 when enabled, else local analysis."""

    INSUFFICIENT_MESSAGE = (
        "The uploaded content does not contain enough story text for a meaningful "
        "summary. Please provide the complete document or additional chapters."
    )

    @classmethod
    def _summary_agent(cls):
        from agents.summary_agent import SummaryAgent
        return SummaryAgent()

    @classmethod
    def _llm_available(cls) -> bool:
        return cls._summary_agent().is_available()

    @classmethod
    def _sentences(cls, text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in parts if len(s.strip()) > 15]

    @classmethod
    def _words(cls, text: str) -> list[str]:
        return re.findall(r"\w+", text)

    @classmethod
    def _word_count(cls, text: str) -> int:
        return len(cls._words(text))

    @classmethod
    def _trim_to_words(cls, text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text.strip()
        return " ".join(words[:max_words]).rstrip(".,;:") + "…"

    @classmethod
    def _clean_pdf_artifacts(cls, text: str) -> str:
        text = re.sub(r"\bI\s+n\b", "In", text)
        text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)
        text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
        text = re.sub(r"([a-z])([A-Z][a-z])", r"\1 \2", text)
        return text

    @classmethod
    def _strip_chapter_header(cls, body: str) -> str:
        lines = body.splitlines()
        while lines:
            first = lines[0].strip()
            if not first:
                lines.pop(0)
                continue
            if re.match(
                r"^(CHAPTER|Chapter|PART|Part|BOOK|Book|ADVENTURE|Adventure)\b",
                first,
                re.I,
            ):
                lines.pop(0)
                continue
            if (
                len(first) < 90
                and first[0].isupper()
                and not first.endswith(".")
                and not first.endswith("?")
                and not first.endswith("!")
            ):
                lines.pop(0)
                continue
            break
        return "\n".join(lines).strip()

    @classmethod
    def _is_junk_sentence(cls, sentence: str) -> bool:
        if any(p.search(sentence) for p in JUNK_SENTENCE_PATTERNS):
            return True
        if re.search(r"\.{3,}", sentence):
            return True
        words = cls._words(sentence)
        if len(words) < 8:
            return True
        upper_ratio = sum(1 for c in sentence if c.isupper()) / max(len(sentence), 1)
        if upper_ratio > 0.35:
            return True
        # Skip bare dialogue fragments
        stripped = sentence.strip()
        if stripped.startswith(('"', "'", "“", "‘")) and len(words) < 20:
            return True
        quote_chars = sum(1 for c in sentence if c in '"\'“”‘’')
        if quote_chars > 4 and len(words) < 25:
            return True
        return False

    @classmethod
    def _story_sentences(cls, text: str) -> list[str]:
        return [s for s in cls._sentences(text) if not cls._is_junk_sentence(s)]

    @classmethod
    def _strip_boilerplate(cls, text: str) -> str:
        text = cls._clean_pdf_artifacts(text)
        text = re.sub(
            r"(?is)\*{0,3}\s*START OF (THE )?PROJECT GUTENBERG.*",
            "",
            text,
        )
        text = re.sub(
            r"(?is)\*{0,3}\s*END OF (THE )?PROJECT GUTENBERG.*",
            "",
            text,
        )

        kept_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                if kept_lines and kept_lines[-1] != "":
                    kept_lines.append("")
                continue
            if any(pattern.search(stripped) for pattern in BOILERPLATE_LINE_PATTERNS):
                continue
            if len(stripped) < 4 and stripped.isdigit():
                continue
            kept_lines.append(stripped)

        cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(kept_lines)).strip()
        return cleaned

    @classmethod
    def _find_story_start(cls, text: str) -> int:
        """Skip title pages, legal notices, and table of contents."""
        for pattern in STORY_START_PATTERNS:
            for match in pattern.finditer(text):
                pos = match.start()
                snippet = text[pos:pos + 800]
                story_sents = cls._story_sentences(snippet)
                if len(story_sents) >= 2:
                    return pos
        # Fallback: first block of real narrative sentences
        for match in re.finditer(r"[.!?]\s+", text):
            chunk = text[match.end():match.end() + 600]
            if len(cls._story_sentences(chunk)) >= 3:
                return match.end()
        return 0

    @classmethod
    def _prepare_narrative(cls, text: str) -> str | None:
        cleaned = cls._strip_boilerplate(text)
        start = cls._find_story_start(cleaned)
        narrative = cleaned[start:].strip()
        if cls._word_count(narrative) < MIN_STORY_WORDS:
            return None
        return narrative

    @classmethod
    def _find_characters(cls, text: str, limit: int = 6) -> list[str]:
        scores: dict[str, int] = {}

        for match in re.finditer(
            r"\b(?:Mr|Mrs|Ms|Dr|Inspector|Colonel|Professor)\.\s+"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            text,
        ):
            name = match.group(1).strip()
            scores[name] = scores.get(name, 0) + 3

        for match in re.finditer(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", text):
            name = match.group(1)
            parts = name.split()
            if any(p in NAME_STOP_WORDS for p in parts):
                continue
            if name.lower() in {"in fact", "in short", "the end", "new york"}:
                continue
            scores[name] = scores.get(name, 0) + 1

        ranked = sorted(scores.items(), key=lambda item: (-item[1], -len(item[0])))
        return [name for name, count in ranked if count >= 3][:limit]

    @classmethod
    def _narrative_starters(cls, sentences: list[str]) -> list[str]:
        starters = [s for s in sentences if s and s[0].isupper()]
        return starters if starters else sentences

    @classmethod
    def _opening_sentences(cls, sentences: list[str], count: int = 4) -> list[str]:
        starters = cls._narrative_starters(sentences)
        preferred = [
            s for s in starters
            if re.match(r"^(In |I |It |He |She |They |The |We |On |At |My )", s)
        ]
        source = preferred if preferred else starters
        return source[:count]

    @classmethod
    def _sample_sentences(cls, sentences: list[str], count: int) -> list[str]:
        starters = cls._narrative_starters(sentences)
        if not starters:
            return []
        if len(starters) <= count:
            return starters
        step = max(1, len(starters) // count)
        return [starters[i] for i in range(0, len(starters), step)][:count]

    @classmethod
    def _to_prose(cls, sentences: list[str], max_words: int = 0) -> str:
        if not sentences:
            return cls.INSUFFICIENT_MESSAGE
        text = " ".join(sentences)
        text = re.sub(r"\s+", " ", text).strip()
        if max_words:
            text = cls._trim_to_words(text, max_words)
        return textwrap.fill(text, width=80)

    @classmethod
    def _split_chapters(cls, text: str) -> list[tuple[str, str]]:
        patterns = [
            re.compile(
                r"(?:^|\n)((?:CHAPTER|Chapter)\s+[IVXLC\d]+[\.:\s][^\n]*)",
                re.MULTILINE,
            ),
            re.compile(
                r"(?:^|\n)((?:The )?Adventure of [^\n]{5,80})",
                re.MULTILINE,
            ),
            re.compile(
                r"(?:^|\n)((?:PART|Part|BOOK|Book)\s+[IVXLC\d]+[\.:\s][^\n]*)",
                re.MULTILINE,
            ),
        ]

        for pattern in patterns:
            matches = list(pattern.finditer(text))
            if len(matches) >= 2:
                chapters = []
                for i, match in enumerate(matches):
                    start = match.start()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                    label = match.group(1).strip()
                    if re.search(r"\.{4,}", label):
                        continue
                    body = text[start:end].strip()
                    body = cls._strip_boilerplate(body)
                    if cls._word_count(body) >= 25 and len(cls._story_sentences(body)) >= 2:
                        chapters.append((label, body))
                if len(chapters) >= 2:
                    return chapters

        words = cls._words(text)
        section_count = min(15, max(5, len(words) // 3000))
        chunk_size = max(400, len(words) // section_count)
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            if chunk_words:
                label = f"Part {len(chunks) + 1}"
                body = " ".join(chunk_words)
                if len(cls._story_sentences(body)) >= 2:
                    chunks.append((label, body))
        return chunks[:15]

    @classmethod
    def _chapter_meta(cls, label: str, body: str, total_words: int) -> dict:
        wc = cls._word_count(body)
        percent = round(100 * wc / total_words) if total_words else 0
        return {
            "title": label,
            "word_count": wc,
            "percent_of_book": percent,
        }

    @classmethod
    def _summarize_chapter_body(cls, label: str, body: str, *, short: bool = False) -> str:
        body = cls._strip_chapter_header(body)
        sentences = cls._story_sentences(body)
        if not sentences:
            return cls.INSUFFICIENT_MESSAGE

        if short:
            picked = [sentences[0]]
            if len(sentences) > 2:
                picked.append(sentences[len(sentences) // 2])
                picked.append(sentences[-1])
            elif len(sentences) > 1:
                picked.append(sentences[-1])
            return cls._to_prose(picked, max_words=80)

        picked = cls._sample_sentences(sentences, 4)
        return cls._to_prose(picked, max_words=120)

    @classmethod
    def generate_short(cls, text: str, title: str) -> str:
        narrative = cls._prepare_narrative(text)
        if not narrative:
            return cls.INSUFFICIENT_MESSAGE

        if cls._llm_available():
            try:
                opening = cls._strip_chapter_header(
                    cls._split_chapters(narrative)[0][1]
                ) if cls._split_chapters(narrative) else narrative[:12000]
                return cls._summary_agent().summarize_text(
                    opening[:12000], title, style="short"
                ).text
            except Exception as exc:
                logger.warning("Llama short summary failed, using local: %s", exc)

        chapters = cls._split_chapters(narrative)
        opening = cls._strip_chapter_header(chapters[0][1]) if chapters else narrative[:8000]
        sentences = cls._story_sentences(opening)
        if not sentences:
            return cls.INSUFFICIENT_MESSAGE

        picked = cls._opening_sentences(sentences, count=4)
        return cls._to_prose(picked, max_words=100)

    @classmethod
    def generate_full_book(cls, text: str, title: str) -> str:
        """Plain narrative story summary — no headings, ready for audio."""
        narrative = cls._prepare_narrative(text)
        if not narrative:
            return cls.INSUFFICIENT_MESSAGE

        if cls._llm_available():
            try:
                agent = cls._summary_agent()
                chapters = cls._split_chapters(narrative)
                if len(chapters) >= 3:
                    picks = [
                        chapters[0],
                        chapters[len(chapters) // 2],
                        chapters[-1],
                    ]
                    parts = []
                    for label, body in picks:
                        body = cls._strip_chapter_header(body)
                        part = agent.summarize_text(
                            body[:12000], title, style="chapter"
                        ).text
                        parts.append(part)
                    combined = "\n\n".join(parts)
                    return agent.summarize_text(
                        f"Combine these plot sections into one continuous story "
                        f"summary of \"{title}\". Write plain prose only, no headings.\n\n"
                        f"{combined}",
                        title,
                        style="full",
                    ).text
                return agent.summarize_text(
                    narrative[:24000], title, style="full"
                ).text
            except Exception as exc:
                logger.warning("Llama full summary failed, using local: %s", exc)

        chapters = cls._split_chapters(narrative)
        paragraphs: list[str] = []

        if len(chapters) >= 2:
            # Summarize opening chapters in order for a coherent story flow
            count = min(8, len(chapters))
            for _label, body in chapters[:count]:
                body = cls._strip_chapter_header(body)
                sents = cls._narrative_starters(cls._story_sentences(body))
                if not sents:
                    continue
                chunk = sents[:2]
                para = cls._to_prose(chunk, max_words=80)
                if para and para != cls.INSUFFICIENT_MESSAGE:
                    paragraphs.append(para)
        else:
            sentences = cls._story_sentences(narrative)
            picked = sentences[:10]
            paragraphs.append(cls._to_prose(picked, max_words=400))

        if not paragraphs:
            return cls.INSUFFICIENT_MESSAGE

        return "\n\n".join(paragraphs)

    @classmethod
    def generate_detailed(cls, text: str, title: str) -> str:
        return cls.generate_full_book(text, title)

    @classmethod
    def generate_chapters(cls, text: str) -> list[dict]:
        narrative = cls._prepare_narrative(text)
        if not narrative:
            return []

        chapters = cls._split_chapters(narrative)
        total_words = cls._word_count(narrative)

        if cls._llm_available():
            try:
                agent = cls._summary_agent()
                llm_results = agent.summarize_chapters(
                    [(lbl, cls._strip_chapter_header(body)) for lbl, body in chapters],
                    short=False,
                    max_chapters=15,
                )
                if llm_results:
                    results = []
                    for item in llm_results:
                        label = item["title"]
                        body = next((b for l, b in chapters if l == label), "")
                        meta = cls._chapter_meta(label, body or item.get("summary", ""), total_words)
                        meta["summary"] = item["summary"]
                        results.append(meta)
                    return results
            except Exception as exc:
                logger.warning("Llama chapter summaries failed, using local: %s", exc)

        results = []

        for label, body in chapters:
            summary = cls._summarize_chapter_body(label, body, short=False)
            if summary == cls.INSUFFICIENT_MESSAGE:
                continue
            item = cls._chapter_meta(label, body, total_words)
            item["summary"] = summary
            results.append(item)

        return results

    @classmethod
    def generate_chapters_short(cls, text: str) -> list[dict]:
        narrative = cls._prepare_narrative(text)
        if not narrative:
            return []

        chapters = cls._split_chapters(narrative)
        total_words = cls._word_count(narrative)

        if cls._llm_available():
            try:
                agent = cls._summary_agent()
                llm_results = agent.summarize_chapters(
                    [(lbl, cls._strip_chapter_header(body)) for lbl, body in chapters],
                    short=True,
                    max_chapters=15,
                )
                if llm_results:
                    results = []
                    for item in llm_results:
                        label = item["title"]
                        body = next((b for l, b in chapters if l == label), "")
                        meta = cls._chapter_meta(label, body or item.get("summary", ""), total_words)
                        meta["summary"] = item["summary"]
                        results.append(meta)
                    return results
            except Exception as exc:
                logger.warning("Llama chapter shorts failed, using local: %s", exc)

        results = []
        for label, body in chapters:
            short = cls._summarize_chapter_body(label, body, short=True)
            if short == cls.INSUFFICIENT_MESSAGE:
                continue
            item = cls._chapter_meta(label, body, total_words)
            item["summary"] = short
            results.append(item)
        return results

    @classmethod
    def generate_main_points(cls, text: str, title: str) -> list[dict]:
        narrative = cls._prepare_narrative(text)
        if not narrative:
            return [{"point": cls.INSUFFICIENT_MESSAGE, "category": "Notice"}]

        sentences = cls._story_sentences(narrative)
        chapters = cls._split_chapters(narrative)
        characters = cls._find_characters(narrative)
        points = []

        if characters:
            points.append({
                "point": f"The story follows {', '.join(characters[:4])}.",
                "category": "Characters",
            })

        step = max(1, len(sentences) // 8)
        for sentence in sentences[::step][:8]:
            points.append({
                "point": sentence[:220],
                "category": "Story",
            })

        for _label, body in chapters[:6]:
            lead = cls._story_sentences(body)
            if not lead:
                continue
            points.append({
                "point": lead[0][:200],
                "category": "Chapter",
            })

        return points[:12]

    @classmethod
    def _condense_chapter_story(cls, label: str, body: str, book_title: str) -> dict | None:
        body = cls._strip_chapter_header(body)
        sentences = cls._story_sentences(body)
        if len(sentences) < 2:
            return None

        selected = []
        indices = [0]
        if len(sentences) > 3:
            indices.extend([
                len(sentences) // 3,
                (2 * len(sentences)) // 3,
                len(sentences) - 1,
            ])
        else:
            indices.extend(range(1, len(sentences)))

        seen = set()
        for idx in indices:
            if idx < len(sentences):
                s = sentences[idx]
                if s not in seen:
                    selected.append(s)
                    seen.add(s)

        content = cls._to_prose(selected, max_words=150)

        return {
            "title": label,
            "content": content,
            "moral": "",
            "source_chapter": label,
            "word_count": cls._word_count(content),
        }

    @classmethod
    def generate_short_stories(cls, text: str, title: str) -> list[dict]:
        narrative = cls._prepare_narrative(text)
        if not narrative:
            return []

        chapters = cls._split_chapters(narrative)

        if cls._llm_available():
            try:
                agent = cls._summary_agent()
                llm_results = agent.summarize_short_stories(
                    [(lbl, cls._strip_chapter_header(body)) for lbl, body in chapters],
                    title,
                    max_chapters=8,
                )
                if llm_results:
                    return llm_results
            except Exception as exc:
                logger.warning("Llama short stories failed, using local: %s", exc)

        results = []

        for label, body in chapters[:10]:
            story = cls._condense_chapter_story(label, body, title)
            if story:
                results.append(story)

        if not results:
            sentences = cls._story_sentences(narrative)
            if len(sentences) >= 2:
                content = cls._to_prose(cls._sample_sentences(sentences, 6), max_words=200)
                results.append({
                    "title": title,
                    "content": content,
                    "moral": "",
                    "source_chapter": "Full story",
                    "word_count": cls._word_count(content),
                })

        return results

    @classmethod
    def generate_reading_guide(cls, text: str, title: str, page_count: int = 0) -> str:
        narrative = cls._prepare_narrative(text)
        if not narrative:
            return cls.INSUFFICIENT_MESSAGE

        chapters = cls._split_chapters(narrative)
        chapter_count = len(chapters)

        parts = [
            f"This is {title}. ",
            "Start with the short summary to get the main story quickly. ",
        ]
        if chapter_count >= 3:
            parts.append(
                f"The book has {chapter_count} parts — read them in order for the full story. "
            )
        parts.append(
            "Use chapter summaries to recap each section, or listen to the short story "
            "versions in Audiobook Studio."
        )
        return textwrap.fill("".join(parts), width=80)

    @classmethod
    def generate_all(cls, text: str, title: str, page_count: int = 0) -> dict:
        return {
            "short_summary": cls.generate_short(text, title),
            "detailed_summary": cls.generate_full_book(text, title),
            "chapter_summaries": cls.generate_chapters(text),
            "chapter_short_summaries": cls.generate_chapters_short(text),
            "main_points": cls.generate_main_points(text, title),
            "short_stories": cls.generate_short_stories(text, title),
            "reading_guide": cls.generate_reading_guide(text, title, page_count),
        }

    @classmethod
    def generate_by_type(cls, summary_type: str, text: str, title: str, page_count: int = 0) -> dict:
        generators = {
            "short": lambda: {"short_summary": cls.generate_short(text, title)},
            "detailed": lambda: {"detailed_summary": cls.generate_full_book(text, title)},
            "full_book": lambda: {"detailed_summary": cls.generate_full_book(text, title)},
            "chapters": lambda: {"chapter_summaries": cls.generate_chapters(text)},
            "chapters_short": lambda: {"chapter_short_summaries": cls.generate_chapters_short(text)},
            "main_points": lambda: {"main_points": cls.generate_main_points(text, title)},
            "short_stories": lambda: {"short_stories": cls.generate_short_stories(text, title)},
            "reading_guide": lambda: {"reading_guide": cls.generate_reading_guide(text, title, page_count)},
            "all": lambda: cls.generate_all(text, title, page_count),
        }
        fn = generators.get(summary_type, generators["all"])
        return fn()

    @classmethod
    def system_prompt(cls) -> str:
        return BOOK_SUMMARIZER_SYSTEM_PROMPT
