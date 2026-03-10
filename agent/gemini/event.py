from typing import List, MutableMapping
from agent.event import EventManager, EventType, Event
from agent.listener import AgentEventListener


class GeminiEventManager(EventManager):
    def __init__(self):
        super().__init__()
        # dict of event types and a list of listeners.
        self._listeners: MutableMapping[EventType, List[AgentEventListener]] = {}

    def subscribe(self, event_type: EventType, listener: AgentEventListener):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: EventType, listener: AgentEventListener):
        if event_type in self._listeners:
            self._listeners[event_type].remove(listener)

    def notify(self, event_type: EventType, event: Event):
        """Notify the listeners for the given event type."""
        if event_type in self._listeners:
            for listener in self._listeners[event_type]:
                listener.handle_event(event)
