from loguru import logger
from agent.event import Event
from agent.listener import AgentEventListener


class GeminiPromptEvaluationListener(AgentEventListener):
    """Listener for triggering a prompt evaluation using google-genai."""
    def __init__(self, chat_session: any):
        """
        :param chat_session: A google.genai chat session.
        """
        self._chat_session = chat_session

    def handle_event(
        self, event: Event
    ) -> bool:
        """Handle a Prompt Evaluation Event."""
        event_data = event.data
        metadata = event_data.get('metadata', {})
        tracing_id = metadata.get('tracingId')
        prompt = event_data.get('prompt')
        
        if not prompt:
            logger.warning(f"No prompt found in event data: {event_data}")
            return False

        try:
            self.__gemini_evaluate_prompt(
                prompt=prompt,
                chat_session=self._chat_session,
            )
        except Exception as e:
            error_msg = (
                f'Encountered exception while evaluating prompt via Agent. '
                f'Tracing ID: {tracing_id}'
            )
            logger.error(f'{error_msg} Error:{e}')
            return False

        return True

    @classmethod
    def __gemini_evaluate_prompt(
        cls,
        prompt: str,
        chat_session: any,
    ) -> str:
        """Invoke Gemini to evaluate the prompt."""
        # In google-genai, we use chat_session.send(message=prompt)
        response = chat_session.send(message=prompt)
        if not response:
            raise ValueError('No response determined from Gemini Agent chat.')
        return response.text


class GeminiConfigurationErrorListener(AgentEventListener):
    def handle_event(self, event: Event) -> bool:
        event_data = event.data
        error_message = event_data.get('errorMessage', 'Unknown configuration error')
        logger.error(f"Gemini Configuration Error: {error_message}")
        return True
