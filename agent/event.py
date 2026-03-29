from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, MutableMapping, List


class EventType(StrEnum):
    # Agent LLM model chat handling.
    AGENT_CHAT_FAILURE = 'agent-chat-failure'
    AGENT_CHAT_SUCCESS = 'agent-chat-success'
    AGENT_CHAT_REQUEST = 'agent-chat-request'

    # Agent LLM model configuration.
    AGENT_CONFIGURATION_FAILURE = 'agent-configuration-failure'
    
    # Tool execution.
    TOOL_CALL_REQUEST = 'tool-call-request'
    TOOL_CALL_SUCCESS = 'tool-call-success'
    TOOL_CALL_FAILURE = 'tool-call-failure'

class Event(ABC):
    """An Event which an Agent sends to the EventListener."""
    @property
    @abstractmethod
    def data(self) -> Any:
        """Return event data."""

    @data.setter
    @abstractmethod
    def data(self, data: Any) -> None:
        """Set event data."""

class GeminiEvent(Event):
    """Wrapper for Gemini Agent event."""
    def __init__(self, **event_data: Any):
        self._data = event_data

    @property
    def data(self) -> dict[str, Any]:
        if not self._data:
             return {}
        return self._data

    @data.setter
    def data(self, data: dict[str, Any]) -> None:
        self._data = data

class EventManager(ABC):
    def __init__(self):
        """
        Constructor.
        """
        # dict of event types and a list of listeners.
        self._listeners: MutableMapping[EventType, List['AgentEventListener']] = {}

    @abstractmethod
    def subscribe(self, event_type: EventType, listener: 'AgentEventListener'):
        """Update the event listener mapping."""

    @abstractmethod
    def unsubscribe(self, event_type: EventType, listener: 'AgentEventListener'):
        """Remove an Event Listener for an Event Type."""

    @abstractmethod
    def notify(self, event_type: EventType, event: Event):
        """Notify the listener that an Agent action resulted in an Event being created."""

# For now, an Event is just a virtual-type of a dict/map
from agent.listener import AgentEventListener
