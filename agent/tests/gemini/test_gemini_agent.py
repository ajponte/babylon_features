import pytest
from unittest.mock import MagicMock, patch
from agent.gemini_agent import GeminiAgent
from agent.event import EventType

@pytest.fixture
def mock_genai_client():
    with patch("google.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_chats = MagicMock()
        mock_client.chats = mock_chats
        
        mock_session = MagicMock()
        mock_chats.create.return_value = mock_session
        
        yield mock_client, mock_session

def test_gemini_agent_initialization(mock_genai_client):
    mock_client, _ = mock_genai_client
    config = {
        'agent': {
            'llm_model': 'gemini-2.0-flash',
            'api_key': 'test-key'
        }
    }
    agent = GeminiAgent(config)
    
    assert agent._harness is not None
    assert agent._chat_session is not None
    
    # Check client initialization
    from google import genai
    mock_client_class = genai.Client
    mock_client_class.assert_called_once_with(api_key='test-key')
    
    # Check session creation
    mock_client.chats.create.assert_called_once_with(
        model='gemini-2.0-flash',
        config={}
    )

def test_gemini_agent_chat_triggers_evaluation(mock_genai_client):
    _, mock_session = mock_genai_client
    mock_session.send.return_value.text = "Mock Response"
    
    config = {
        'agent': {
            'llm_model': 'gemini-2.0-flash',
            'api_key': 'test-key'
        }
    }
    agent = GeminiAgent(config)
    
    # Mock the notify to verify it's called
    with patch.object(agent._harness.events, 'notify', wraps=agent._harness.events.notify) as mock_notify:
        agent.chat("Test Prompt")
        
        # Verify notify was called with AGENT_CHAT_REQUEST
        mock_notify.assert_called_once()
        args, kwargs = mock_notify.call_args
        # In GeminiEventManager.notify: (self, event_type: EventType, event: Event)
        # Depending on how it was called, it might be in args or kwargs.
        
        if 'event' in kwargs:
            event = kwargs['event']
        else:
            event = args[1]
            
        assert event.data['prompt'] == "Test Prompt"
        
    # Since prompt evaluation listener is registered, it should call send on session
    mock_session.send.assert_called_once_with(message="Test Prompt")
