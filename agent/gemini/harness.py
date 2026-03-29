from typing import Callable, Any
from google import genai
from loguru import logger

from agent.agent_harness import AgentHarness
from agent.error import AgentConfigurationError
from agent.event import EventType, GeminiEvent
from agent.gemini.event import GeminiEventManager
from agent.utils import get_now, generate_random_uuid


class GeminiAgentHarness(AgentHarness):
    """The Harness for Gemini Agents using the unified google-genai SDK."""
    def __init__(
        self,
        model_name: str,
        tools: list | None = None,
        agent_id: str | None = None,
        api_key: str | None = None
    ):
        """
        Constructor.

        :param model_name: Gemini model name.
        :param tools: List of allowed tool functions.
        :param agent_id: Unique ID of the Agent this Harness manages.
        :param api_key: Gemini API key.
        """
        super().__init__()
        self.events = GeminiEventManager()
        self._model_name = model_name
        self._agent_id = self.__handle_agent_id(model=model_name, agent_id=agent_id)
        
        try:
            self._client = _configure_genai_client(api_key=api_key)
            self._tools = tools
        except Exception as e:
            message = f"Failed to configure Gemini client: {e}"
            logger.exception(message)
            send_configuration_failure(
                event_manager=self.events,
                model_name=model_name,
                agent_id=self._agent_id,
                message=message
            )
            raise AgentConfigurationError(message=message) from e

    def start_chat_session(
        self,
        enable_automatic_function_calling: bool = False,
        tracing_id: str | None = None
    ) -> Any:
        """
        Start a chat session with the Gemini Agent.
        """
        try:
            # In google-genai, we use client.chats.create
            # config={'tools': self._tools} if tools are provided
            chat_config = {}
            if self._tools:
                chat_config['tools'] = self._tools
            
            # Note: automatic function calling is often handled via the config in the new SDK
            # but for now we follow the existing pattern of passing it.
            
            chat = self._client.chats.create(
                model=self._model_name,
                config=chat_config
            )
            return chat
        except Exception as e:
            err_msg = f'Failed to start a chat with the Gemini agent: {e}'
            logger.debug(f'{err_msg}')
            send_agent_chat_failure(
                event_manager=self.events,
                model_name=self._model_name,
                agent_id=self._agent_id,
                tracing_id=tracing_id,
                message=err_msg
            )
            raise ValueError(err_msg) from e

    def execute(
        self,
        prompt: str,
        chat_session: Any
    ) -> None:
        """
        Execute the user's prompt query. Notify the listener via the EventManger as needed.

        :param prompt: A prompt to execute.
        :param chat_session: An open chat session with an Agent.
        """
        self.send_agent_chat_event(prompt=prompt)

    def send_agent_chat_event(
        self,
        prompt: str,
        tracing_id: str | None = None
    ):
        """Trigger a chat request event."""
        send_agent_chat_event(
            event_manager=self.events,
            model_name=self._model_name,
            agent_id=self._agent_id,
            prompt=prompt,
            tracing_id=tracing_id
        )

    def send_tool_call_event(
        self,
        tool_name: str,
        arguments: dict,
        tracing_id: str | None = None
    ):
        """Trigger a tool call request event."""
        send_tool_call_event(
            event_manager=self.events,
            model_name=self._model_name,
            agent_id=self._agent_id,
            tool_name=tool_name,
            arguments=arguments,
            tracing_id=tracing_id
        )

    def send_tool_call_success(
        self,
        tool_name: str,
        result: Any,
        tracing_id: str | None = None
    ):
        """Trigger a tool call success event."""
        send_tool_call_success(
            event_manager=self.events,
            model_name=self._model_name,
            agent_id=self._agent_id,
            tool_name=tool_name,
            result=result,
            tracing_id=tracing_id
        )

    def send_tool_call_failure(
        self,
        tool_name: str,
        error: str,
        tracing_id: str | None = None
    ):
        """Trigger a tool call failure event."""
        send_tool_call_failure(
            event_manager=self.events,
            model_name=self._model_name,
            agent_id=self._agent_id,
            tool_name=tool_name,
            error=error,
            tracing_id=tracing_id
        )

    @classmethod
    def __handle_agent_id(
        cls, model: str, agent_id: str | None
    ) -> str:
        """Assign a random ID for an Agent, if needed."""
        if not agent_id:
            agent_id = generate_random_uuid()
            logger.info(f'Assigning random ID {agent_id} to new Agent for {model}')
        return agent_id


def _configure_genai_client(api_key: str | None = None) -> genai.Client:
    """
    Configure and return a google-genai Client.
    """
    import os
    final_api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
    if not final_api_key:
        raise ValueError(
            'Unable to configure a Gemini client. No API key provided.'
        )
    
    return genai.Client(api_key=final_api_key)


def send_configuration_failure(
    event_manager: GeminiEventManager,
    model_name: str,
    agent_id: str,
    message: str
) -> None:
    event_manager.notify(
        EventType.AGENT_CONFIGURATION_FAILURE,
        event=GeminiEvent(
            metadata={
                'occurredAt': get_now(),
                'modelName': model_name,
                'agentId': agent_id,
            },
            errorMessage=message
        )
    )

def send_agent_chat_failure(
    event_manager: GeminiEventManager,
    model_name: str,
    agent_id: str,
    tracing_id: str | None,
    message: str,
):
    event_manager.notify(
        EventType.AGENT_CHAT_FAILURE,
        event=GeminiEvent(
            metadata={
                'model': model_name,
                'agentId': agent_id,
                'tracingId': tracing_id,
                'occurredAt': get_now(),
            },
            errorMessage=message
        )
    )

def send_agent_chat_event(
    event_manager: GeminiEventManager,
    model_name: str,
    agent_id: str,
    tracing_id: str | None,
    prompt: str,
):
    event_manager.notify(
        EventType.AGENT_CHAT_REQUEST,
        event=GeminiEvent(
            metadata={
                'model': model_name,
                'agentId': agent_id,
                'tracingId': tracing_id,
                'occurredAt': get_now(),
            },
            prompt=prompt
        )
    )

def send_tool_call_event(
    event_manager: GeminiEventManager,
    model_name: str,
    agent_id: str,
    tool_name: str,
    arguments: dict,
    tracing_id: str | None,
):
    event_manager.notify(
        EventType.TOOL_CALL_REQUEST,
        event=GeminiEvent(
            metadata={
                'model': model_name,
                'agentId': agent_id,
                'tracingId': tracing_id,
                'occurredAt': get_now(),
            },
            toolName=tool_name,
            arguments=arguments
        )
    )

def send_tool_call_success(
    event_manager: GeminiEventManager,
    model_name: str,
    agent_id: str,
    tool_name: str,
    result: Any,
    tracing_id: str | None,
):
    event_manager.notify(
        EventType.TOOL_CALL_SUCCESS,
        event=GeminiEvent(
            metadata={
                'model': model_name,
                'agentId': agent_id,
                'tracingId': tracing_id,
                'occurredAt': get_now(),
            },
            toolName=tool_name,
            result=result
        )
    )

def send_tool_call_failure(
    event_manager: GeminiEventManager,
    model_name: str,
    agent_id: str,
    tool_name: str,
    error: str,
    tracing_id: str | None,
):
    event_manager.notify(
        EventType.TOOL_CALL_FAILURE,
        event=GeminiEvent(
            metadata={
                'model': model_name,
                'agentId': agent_id,
                'tracingId': tracing_id,
                'occurredAt': get_now(),
            },
            toolName=tool_name,
            errorMessage=error
        )
    )
