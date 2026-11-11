"""Port for anything that answers a chat turn by emitting pipeline events."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol

from pydantic import BaseModel

from finsage_replica.domain.events import Event


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatPipeline(Protocol):
    name: str

    def run(self, question: str, history: list[Turn]) -> AsyncIterator[Event]:
        """Events of one run, from `run_started` to `done` (or `error`)."""
        ...
