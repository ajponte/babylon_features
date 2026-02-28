from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from agent.event import EventType, EventsManager
from agent.listener import AgentEventListener

Tool = TypeVar('Tool')


class Agent(ABC, Generic[Tool]):
    """A generalized agent responsible for session."""
    def __init__(self):
        """
        Constructor.
        """
        events: EventsManager

    def run_tool(self, tool: Generic[Tool]) -> None:
        """
        Execute a tool call.

        :param tool: The tool to run.
        """


class AgentHarness(ABC, Generic[Tool]):
    """
    Observer object to monitor agent execution.
    """
    def __init__(self):
        """
        Constructor.
        """
        self.events: EventsManager
        # Represents a pointer to some tool being executed.
        self.current_tool_execution: Generic[Tool]

    @abstractmethod
    def configure_agent(self) -> Agent:
        """
        Configure and return a new Agent.

        :return:
        """

    @abstractmethod
    def execute_tool_call(self, tool: Any) -> None:
        """Have the agent execute the tool call."""
        if self.current_tool_execution is not None:
            del self.current_tool_execution
        self.current_tool_execution = tool.name
        self.events.notify(tool, tool.name)
        return None
