import uuid
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Any, Callable, Dict
from functools import wraps

from agent.event import EventManager

ToolType = TypeVar('ToolType')
UserPrompt = TypeVar('UserPrompt')
AgentResponse = TypeVar('AgentResponse')
AgentChatSession = TypeVar('AgentChatSession')


class Agent(ABC, Generic[ToolType]):
    """A generalized agent responsible for session."""
    def __init__(self):
        """
        Constructor.
        """
        self.events: EventManager

    @abstractmethod
    def run_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool call.
        """


class AgentHarness(ABC, Generic[AgentChatSession, AgentResponse, ToolType, UserPrompt]):
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
        prompt: UserPrompt,
        chat_session: AgentChatSession
    ) -> None:
        """
        Execute the user's prompt query. Notify the listener via the EventManger as needed.
        """

def observe_tool(harness: 'AgentHarness'):
    """
    Decorator to wrap a tool function with harness events.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tool_name = func.__name__
            # Attempt to send request event.
            try:
                # We need a way to call harness.send_tool_call_event but it's not in the base class.
                # For now we'll assume the harness has it or we use a more generic notify.
                if hasattr(harness, 'send_tool_call_event'):
                    harness.send_tool_call_event(tool_name=tool_name, arguments=kwargs)
            except Exception:
                pass

            try:
                result = func(*args, **kwargs)
                if hasattr(harness, 'send_tool_call_success'):
                    harness.send_tool_call_success(tool_name=tool_name, result=result)
                return result
            except Exception as e:
                if hasattr(harness, 'send_tool_call_failure'):
                    harness.send_tool_call_failure(tool_name=tool_name, error=str(e))
                raise e
        return wrapper
    return decorator
