from abc import ABC, abstractmethod
from agent.event import Event


class AgentEventListener(ABC):
    """Listens for Agent events."""

    @abstractmethod
    def handle_event(self, event: Event) -> bool:
        """Handle an event."""
