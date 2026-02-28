from loguru import logger

from agent.event import EventsManager, EventType
from agent.listener import AgentEventListener


class GeminiEventsManager(EventsManager):
    def __init__(self):
        self.listeners: dict | None = None
        super(EventsManager).__init__()

    @property
    def listeners(self) -> dict | None:
        return self.listeners

    def subscribe(self, event_type: EventType, listener: AgentEventListener):
        self.listeners[event_type] = listener

    def unsubscribe(self, event_type: EventType):
        self.listeners.pop(event_type)

    def notify(self):