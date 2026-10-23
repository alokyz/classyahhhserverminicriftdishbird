"""Server adapter contracts and the standard Java status implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .config import Settings


class ServerAdapter(Protocol):
    """Interface implemented by read-only server integrations."""

    name: str

    def status(self) -> tuple[dict[str, Any] | None, str]:
        """Return a status payload and online/offline/unknown state."""


@dataclass(frozen=True, slots=True)
class JavaStatusAdapter:
    """Standard Java status protocol, applicable across configured server types."""

    settings: Settings
    name: str = "java-status"

    def status(self) -> tuple[dict[str, Any] | None, str]:
        # Lazy import keeps the wire-protocol helpers grouped with monitoring
        # without creating a module import cycle.
        from .monitoring import query_java_status

        return query_java_status(self.settings)


def create_server_adapter(settings: Settings) -> ServerAdapter:
    """Return a read-only adapter; server-specific launch handling is not inferred."""
    return JavaStatusAdapter(settings)
