import uuid
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type

from agent.event import EventManager

Tool = TypeVar('Tool')
UserPrompt = TypeVar('UserPrompt')
AgentResponse = TypeVar('AgentResponse')
AgentChatSession = TypeVar('AgentChatSession')


class Agent(ABC, Generic[Tool]):
    """A generalized agent responsible for session."""
    def __init__(self):
        """
        Constructor.
        """
        events: EventManager

    def run_tool(self, tool: Generic[Tool]) -> None:
        """
        Execute a tool call.

        :param tool: The tool to run.
        """


class AgentHarness(ABC, Generic[AgentChatSession, AgentResponse, Tool, UserPrompt]):
    """
    Observer object to monitor agent execution.
    """
    def __init__(self):
        """
        Constructor.
        """
        self.events: EventManager

    @abstractmethod
    def execute(
        self,
        prompt: Type[UserPrompt],
        chat_session: Type[AgentChatSession]
    ) -> None:
        """
        Execute the user's prompt query. Notify the listener via the EventManger as needed.

        :param prompt: A prompt to execute.
        :param chat_session: An open chat session with an Agent.
        """
