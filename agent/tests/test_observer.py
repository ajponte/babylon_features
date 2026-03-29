import pytest
from unittest.mock import MagicMock
from agent.event import EventType, Event, GeminiEvent
from agent.gemini.event import GeminiEventManager
from agent.listener import AgentEventListener

class MockListener(AgentEventListener):
    def __init__(self):
        self.called = False
        self.received_event = None

    def handle_event(self, event: Event) -> bool:
        self.called = True
        self.received_event = event
        return True

def test_event_manager_subscribe_notify():
    manager = GeminiEventManager()
    listener = MockListener()
    
    manager.subscribe(EventType.AGENT_CHAT_REQUEST, listener)
    
    event = GeminiEvent(prompt="Hello World")
    manager.notify(EventType.AGENT_CHAT_REQUEST, event)
    
    assert listener.called is True
    assert listener.received_event == event
    assert listener.received_event.data['prompt'] == "Hello World"

def test_event_manager_unsubscribe():
    manager = GeminiEventManager()
    listener = MockListener()
    
    manager.subscribe(EventType.AGENT_CHAT_REQUEST, listener)
    manager.unsubscribe(EventType.AGENT_CHAT_REQUEST, listener)
    
    event = GeminiEvent(prompt="Hello World")
    manager.notify(EventType.AGENT_CHAT_REQUEST, event)
    
    assert listener.called is False

def test_event_manager_multiple_listeners():
    manager = GeminiEventManager()
    listener1 = MockListener()
    listener2 = MockListener()
    
    manager.subscribe(EventType.AGENT_CHAT_REQUEST, listener1)
    manager.subscribe(EventType.AGENT_CHAT_REQUEST, listener2)
    
    event = GeminiEvent(prompt="Hello World")
    manager.notify(EventType.AGENT_CHAT_REQUEST, event)
    
    assert listener1.called is True
    assert listener2.called is True
