# pylint: disable=unused-variable
# pylint: disable=unused-argument
"""Step for querying the Babylon Data Lake"""

from typing import Annotated

from zenml import step


@step
def query_data_lake(
    transaction_descriptions: list[str] | None = None,
    mock: bool = False,
) -> Annotated[list, "raw_documents"]:
    """Entry point to query the datalake for new documents.

    :param transaction_descriptions: Optional list of transaction descriptions.
    :param mock: Whether to return mock data.
    """
    if mock:
        return [
            {"id": "1", "content": "Sample transaction 1", "metadata": {"source": "mock"}},
            {"id": "2", "content": "Sample transaction 2", "metadata": {"source": "mock"}},
        ]
    documents: list = []
    # todo
    return documents
