class RAGError(Exception):
    def __init__(self, message: str, cause: Exception | None = None):
        self._message = message
        self._cause = cause

    @property
    def message(self) -> str:
        return self._message

    @property
    def cause(self) -> Exception | None:
        return self._cause

class DatalakeError(Exception):
    def __init__(self, message: str, cause: Exception | None = None):
        self._message = message
        self._cause = cause

    @property
    def message(self) -> str:
        return self._message

    @property
    def cause(self) -> Exception | None:
        return self._cause

class DocumentsCollectionError(BaseException):
    """
    Throw this error when there's an issue operating on
    a collection of documents.
    """
    def __init__(self, message: str, cause: Exception | None = None):
        self._message = message
        self._cause = cause

    @property
    def message(self) -> str:
        return self._message

    @property
    def cause(self) -> Exception | None:
        return self._cause
