from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Mapping

from agent.listener import AgentEventListener


class EventType(StrEnum):
    # Agent LLM model chat handling.
    AGENT_CHAT_FAILURE = 'agent-chat-failure'
    AGENT_CHAT_SUCCESS = 'agent-chat-failure'
    AGENT_CHAT_REQUEST = 'agent-chat-request'

    # Agent LLM model configuration.
    AGENT_CONFIGURATION_FAILURE = 'agent-configuration-failure'

class Event(ABC):
    """An Event which an Agent sends to the EventListener."""
    @abstractmethod
    @property
    def data(self) -> Any:
        """Return event data."""

    @data.setter
    @abstractmethod
    def data(self, data: Any) -> None:
        """Set event data."""

class GeminiEvent(Event):
    """Wrapper for Gemini Agent event."""
    def __init__(self, **event_data: dict[str, Any]):
        self._data = event_data

    def data(self, **data) -> dict[str, Any]:
        if not self._data:
            raise ValueError("Gemini Event holds no data.")
        return self._data

class EventManager(ABC):
    def __init__(self):
        """
        Constructor.
        """
        # dict/hashmap of event types and listeners.
        self.listeners: Mapping[EventType, AgentEventListener]

    @abstractmethod
    def subscribe(self, event_type: EventType, listener: AgentEventListener):
        """Update the event listener mapping."""

    @abstractmethod
    def unsubscribe(self, event_type: EventType):
        """Remove an Event Listener for an Event Type."""

    @abstractmethod
    def notify(self, event_type: EventType, data: Mapping):
        """Notify the listener that an Agent action resulted in an Event being created."""

# For now, an Event is just a virtual-type of a dict/map
Event.register(dict[str, Any])
