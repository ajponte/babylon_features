from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Mapping

from agent.listener import AgentEventListener


class EventType(StrEnum):
    AGENT_TOOL_CALL_SUCCESS = 'agent-tool-call-success'
    AGENT_TOOL_CALL_FAILURE = 'agent-tool-call-failure'

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


class EventsManager(ABC):
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
    def notify(self):
        """Notify the calling Agent of an the result of an action or event."""

# For now, an Event is just a virtual-type of a dict/map
Event.register(dict[str, Any])
