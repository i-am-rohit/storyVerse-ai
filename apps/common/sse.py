"""Server-Sent Events helpers for streaming AI generation."""

import json
from collections.abc import Iterator


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def sse_progress(message: str, percent: int = 0, **extra) -> str:
    payload = {"message": message, "percent": percent, **extra}
    return sse("progress", payload)


def sse_token(text: str) -> str:
    return sse("token", {"text": text})


def sse_complete(data: dict) -> str:
    return sse("complete", data)


def sse_error(message: str) -> str:
    return sse("error", {"error": message})


def format_event(event_dict: dict) -> str:
    event = event_dict["event"]
    data = {key: value for key, value in event_dict.items() if key != "event"}
    return sse(event, data)
