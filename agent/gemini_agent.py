"""Driver class for a Gemini Agent."""
from agent.event import EventType
from agent.gemini.listener import (
    GeminiPromptEvaluationListener,
    GeminiConfigurationErrorListener
)
from agent.gemini.load import load_harness


class GeminiAgent:
    """Abstraction for a Gemini Agent."""
    def __init__(self, config: dict, tools: list | None = None):
        api_key = config.get('agent', {}).get('api_key')
        self._harness = load_harness(config=config, tools=tools, api_key=api_key)
        
        enable_afc = config.get('agent', {}).get('enable_automatic_function_calling', False)
        self._chat_session = self._harness.start_chat_session(
            enable_automatic_function_calling=enable_afc
        )
        
        # Setup listeners after session is created as they might need it.
        self._setup_listeners()

    def chat(self, prompt: str, tracing_id: str | None = None):
        """Trigger evaluation via the Event Manager."""
        self._harness.execute(
            prompt=prompt,
            chat_session=self._chat_session
        )

    def _setup_listeners(self):
        # Listener for chat events.
        prompt_evaluation_listener = GeminiPromptEvaluationListener(
            chat_session=self._chat_session
        )
        # Subscribe to the listener.
        self._harness.events.subscribe(
            EventType.AGENT_CHAT_REQUEST,
            listener=prompt_evaluation_listener
        )

        # Listener for chat error events.
        chat_error_listener = GeminiConfigurationErrorListener()
        self._harness.events.subscribe(
            EventType.AGENT_CHAT_FAILURE,
            listener=chat_error_listener
        )
