import google.generativeai as gemini
from google.generativeai import ChatSession

from loguru import logger

from agent.agent_harness import AgentHarness
from agent.error import AgentConfigurationError
from agent.event import EventType
from agent.gemini.event import GeminiEventManager
from typing import Callable

from agent.utils import get_now, generate_random_uuid


class GeminiAgentHarness(AgentHarness):
    """The Harness for Gemini Agents."""
    def __init__(
        self,
        model_name: str,
        tools: list,
        agent_id: str | None
    ):
        """
        Constructor.

        :param model_name: Gemini model name.
        :param tools: List of allowed tool functions.
        :param agent_id: Unique ID of the Agent this Harness manages.
        """
        super(AgentHarness).__init__()
        self.events = GeminiEventManager()
        self._model_name = model_name
        self._agent_id = self.__handle_agent_id(model=model_name, agent_id=agent_id)
        try:
            self._llm_model: gemini = _configure_gemini_agent(
                tools=tools,
                model_name=self._model_name
            )
        except Exception as e:
            message = "Failed to configure gemini agent"
            logger.exception(message)

            # Notify listener.
            send_configuration_failure(
                event_manager=self.events,
                model_name=model_name,
                agent_id=agent_id,
                message=message
            )

    def start_chat_session(
        self,
        enable_automatic_function_calling: bool=False,
        tracing_id: str|None = None
    ) -> ChatSession:
        """
        Start a chat with the Gemini Agent.

        :param enable_automatic_function_calling: When True, tool functions will automatically
                                                  be called when evaluating the prompt.
                                                  This is essentially what handles a "chat session loop"
                                                  with the agent.
        :param tracing_id: Optional tracing ID to track the chat session from upstream processes.
        :return: A newly opened chat session, this object publishes events to the listener via `GeminiEventManager`.
                 upon success or failure.
        """
        chat: ChatSession| None = self.__start_chat_with_gemini_agent(
            enable_automatic_function_calling=enable_automatic_function_calling,
            tracing_id=tracing_id
        )

        return chat

    def send_agent_chat_event(
        self,
        prompt: str,
        tracing_id: str|None = None
    ):
        """Trigger a chat event."""
        send_agent_chat_event(
            event_manager=self.events,
            model_name=self._model_name,
            agent_id=self._agent_id,
            prompt=prompt,
            tracing_id=tracing_id
        )


    def __start_chat_with_gemini_agent(
        self,
        enable_automatic_function_calling: bool,
        tracing_id: str | None=None
    ) -> ChatSession:
        chat: ChatSession | None = None
        try:
            chat = self._llm_model.start_chat(
                enable_automatic_function_calling=enable_automatic_function_calling
            )
            return chat
        except Exception as e:
            err_msg = 'Failed to start a chat with the gemini agent.'
            logger.debug(f'{err_msg} Error: {e}')

            # Notify the listener of failure.
            send_agent_chat_failure(
                event_manager=self.events,
                model_name=self._model_name,
                agent_id=self._agent_id,
                tracing_id=tracing_id,
                message=err_msg
            )
        if not chat:
            raise ValueError('No chat response determined.')
        return chat

    @classmethod
    def __handle_agent_id(
        cls, model: str, agent_id: str|None
    ) -> str:
        """Assign a random ID for an Agent, if needed."""
        if not agent_id:
            logger.info(f'Assigning random ID to new Agent for {model}')
            agent_id = generate_random_uuid()
        return agent_id


def _configure_gemini_agent(
    model_name: str,
    tools: list[Callable],
    **kwargs
) -> gemini:
    """
    Configure and return a gemini agent instance.

    :param model_name: Name of the gemini model.
    :param tools: List of available tool call functions.
    :return: A new agent.
    """
    gemini_api_key: str | None = kwargs.pop('gemini-api-key')
    if not gemini_api_key:
        raise ValueError(
            'Unable to configure a gemini agent. No API key provided.'
        )
    try:
        gemini.configure(api_key=gemini_api_key)
        model = gemini.GenerativeModel(
            model_name=model_name,
            tools=tools,
        )
        return model

    except Exception as e:
        error_message = 'Failed to configure a gemini agent.'
        raise AgentConfigurationError(
            message=error_message, cause=e) from e


def send_configuration_failure(
    event_manager: GeminiEventManager,
    model_name: str,
    agent_id: str,
    message: str
) -> None:
    """
    Notify the event listener of an agent configuration failure.

    :param event_manager:Event Manager
    :param model_name: Gemini model name.
    :param agent_id: Agent ID.
    :param message: Error message.
    :return:
    """
    event_manager.notify(
        EventType.AGENT_CONFIGURATION_FAILURE,
        data={
            'metadata': {
                'occurredAt': get_now(),
                'modelName': model_name,
                'agentId': agent_id,
            },
            'errorMessage': message
        }
)

def send_agent_chat_failure(
    event_manager: GeminiEventManager,
    model_name: str,
    agent_id: str,
    tracing_id: str,
    message: str,
):
    """
    Notify the event listener of an agent chat failure.

    :param event_manager:Event Manager
    :param model_name: Gemini model name.
    :param agent_id: Agent ID.
    :param tracing_id: Optional tracing ID.
    :param message: Error message.
    """
    event_manager.notify(
        EventType.AGENT_CHAT_FAILURE,
        data={
            'metadata': {
                'model': model_name,
                'agentId': agent_id,
                'tracingId': tracing_id,
                'occurredAt': get_now(),
            },
            'errorMessage': message
        }
    )

def send_agent_chat_event(
    event_manager: GeminiEventManager,
    model_name: str,
    agent_id: str,
    tracing_id: str,
    prompt: str,
):
    """
    Notify the event listener of an agent chat event.

    :param event_manager:Event Manager
    :param model_name: Gemini model name.
    :param agent_id: Agent ID.
    :param tracing_id: Optional tracing ID.
    :param prompt: prompt message.
    """
    event_manager.notify(
        EventType.AGENT_CHAT_REQUEST,
        data={
            'metadata': {
                'model': model_name,
                'agentId': agent_id,
                'tracingId': tracing_id,
                'occurredAt': get_now(),
            },
            'userPrompt': prompt
        }
    )
