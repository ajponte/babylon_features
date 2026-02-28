from abc import ABC, abstractmethod
from typing import Any

from agent.event import Event


class AgentEventListener(ABC):
    """Listens for Agent events."""

    @abstractmethod
    @property
    def event(self) -> Event:
        """Return this listener's event data."""

    @event.setter
    @abstractmethod
    def event(self, event_data: Any) -> None:
        """Set.update the event data for this listener instance."""

    @abstractmethod
    def clear_event(self) -> None:
        """Remove any references to an Event this listener might hold."""
