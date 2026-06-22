"""Story review agent — evaluates and refines generated content."""

from dataclasses import dataclass


@dataclass
class ReviewResult:
    score: float
    feedback: list[str]
    revised_content: str | None = None


class ReviewerAgent:
    """Reviews story drafts for quality, coherence, and style."""

    def review(self, content: str) -> ReviewResult:
        raise NotImplementedError("ReviewerAgent.review() is not yet implemented.")
