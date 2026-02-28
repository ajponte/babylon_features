from agent.event import EventManager, EventType
from agent.listener import AgentEventListener, GeminiPromptEvaluation


class GeminiEventManager(EventManager):
    def __init__(self):
        super(EventManager).__init__()

    @property
    def listeners(self) -> dict | None:
        return self.listeners

    def subscribe(self, event_type: EventType, listener: AgentEventListener):
        self.listeners[event_type] = listener

    def unsubscribe(self, event_type: EventType):
        self.listeners.pop(event_type)

    def notify(self, event_type: EventType, data):
        """Notify the listener that a Gemini Agent action resulted in an Event being created."""
        # Dispatch listeners
        for listener in self.listeners:
            listener.handle_event(data)
