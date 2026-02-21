# pylint: disable=unused-variable
# pylint: disable=unused-argument
"""Step for querying the Babylon Data Lake"""

from typing import Annotated

from zenml import step


@step
def query_data_lake(
    transaction_descriptions: list[str] | None = None,
) -> Annotated[list, "raw_documents"]:
    """Entry point to query the datalake for new documents.

    :param transaction_descriptions: Optional list of
    """
    documents: list = []
    # todo
    return documents
