"""Step for querying the Babylon Data Lake"""
from typing import Annotated

from zenml import step

@step
def query_data_lake(
    transaction_descriptions: list[str],
) -> Annotated[list, "raw_documents"]:
    """Entry point to query the datalake for new documents.

    :param transaction_descriptions: Optional list of
    """
    documents = []
    # todo
    return documents
