"""Story planning agent — outlines story structure and chapters."""

from dataclasses import dataclass


@dataclass
class StoryPlan:
    title: str
    genre: str
    outline: list[str]


class PlannerAgent:
    """Generates story outlines and chapter plans."""

    def plan(self, prompt: str, genre: str = "fiction") -> StoryPlan:
        raise NotImplementedError("PlannerAgent.plan() is not yet implemented.")
