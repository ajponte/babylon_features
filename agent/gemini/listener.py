from loguru import logger

from agent.error import AgentConfigurationError
from agent.event import Event
from agent.listener import AgentEventListener
import google.generativeai as gemini
from google.generativeai import ChatSession


class GeminiPromptEvaluationListener(AgentEventListener):
    """Listener for triggering a prompt evaluation."""
    def __init__(self, chat_session: ChatSession):
        self._chat_session = chat_session

    def handle_event(
        self, event: Event
    ) -> bool:
        """Handle a Prompt Evaluation Event."""
        event_data = event.data
        tracing_id = event_data.get('tracingId')
        try:
            self.__gemini_evaluate_prompt(
                prompt=event_data['prompt'],
                chat_session=self._chat_session,
            )
        except Exception as e:
            error_msg = (
                'Encountered unknown exception while sending prompt to Agent. '
                f'Tracing ID: {tracing_id}'
            )
            logger.debug(f'{error_msg} Error:{e}')
            logger.info(error_msg)

            return False

        return True

    @classmethod
    def __gemini_evaluate_prompt(
        cls,
        prompt: str,
        chat_session: ChatSession,
    ) -> str:
        """Invoke Gemini to evaluate the prompt and return the text response."""
        response = chat_session.send_message(prompt)
        if not response:
            raise ValueError('No response determined from Gemini Agent chat.')
        return response.text


class GeminiConfigurationErrorListener(AgentEventListener):
    def handle_event(self, event: Event) -> bool:
        event_data = event.data
        event_metadata = event_data['metadata']
        raise AgentConfigurationError(
            message=event_metadata.message,
        )
