"""Small in-process SSE event log; durable status remains in project.json."""

from __future__ import annotations

import threading
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from framefoley_api.models import SseEvent, SseEventType


class EventLog:
    def __init__(self, *, max_events: int = 500) -> None:
        self._events: dict[str, list[SseEvent]] = defaultdict(list)
        self._lock = threading.Lock()
        self._max_events = max_events

    def publish(
        self,
        project_id: str,
        event_type: SseEventType,
        payload: dict[str, Any],
        *,
        event_id: str | None = None,
        candidate_id: str | None = None,
    ) -> SseEvent:
        event = SseEvent(
            type=event_type,
            project_id=project_id,
            event_id=event_id,
            candidate_id=candidate_id,
            at=datetime.now(UTC),
            payload=payload,
        )
        with self._lock:
            project_events = self._events[project_id]
            project_events.append(event)
            if len(project_events) > self._max_events:
                del project_events[: len(project_events) - self._max_events]
        return event

    def since(self, project_id: str, cursor: int) -> tuple[list[SseEvent], int]:
        with self._lock:
            events = list(self._events.get(project_id, []))
        return events[cursor:], len(events)
