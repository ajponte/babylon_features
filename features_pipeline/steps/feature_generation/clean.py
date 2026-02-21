# pylint: disable=unused-variable
# pylint: disable=unused-argument
"""The cleaning step for the pipeline. This step cleans fetched
documents from the Babylon Data Lake.
"""

from typing import Annotated

from zenml.steps import step


@step
def clean_documents(
    documents: Annotated[list, "raw_documents"],
) -> Annotated[list, "cleaned_documents"]:
    """Entry point to clean a list of datalake documents."""
    cleaned_documents: list = []
    # todo
    return cleaned_documents
