"""
Lightweight broadcaster for status updates (SSE-friendly).
"""

from __future__ import annotations

import asyncio
from typing import Set


class StatusBroadcaster:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)

    def publish(self, message: str) -> None:
        subscribers = list(self._subscribers)
        if not subscribers:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        for queue in subscribers:
            if loop and not loop.is_closed():
                loop.call_soon_threadsafe(queue.put_nowait, message)
            else:
                queue.put_nowait(message)


broadcaster = StatusBroadcaster()

