class AgentError(Exception):
    def __init__(self, message: str, cause: Exception | None = None):
        """
        Constructor.

        :param message: Error message.
        :param cause: Error cause.
        """
        self._message = message
        self._cause = cause

    @property
    def message(self) -> str:
        """Return error message."""
        return self._message

    @property
    def cause(self) -> Exception:
        """Return error cause."""
        return self._cause


class AgentConfigurationError(AgentError):
    """Raise this error when there's a problem configuring a chat agent."""
    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message=message, cause=cause)


class AgentChatError(AgentError):
    """Raise this error when there's a problem starting a chat with an agent."""
    def __init__(self, message: str, cause: Exception | None):
        super().__init__(message=message, cause=cause)
