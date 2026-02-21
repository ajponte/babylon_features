# pylint: disable=unused-variable
# pylint: disable=unused-argument
"""Step for loading cleaned vectors to the vector store."""

from typing import Annotated
from zenml import step

from features_pipeline.logger import get_logger

_LOGGER = get_logger()


@step
def load_to_vector_db(
    documents: Annotated[list, "documents"],
) -> Annotated[bool, "successful"]:
    """Entry point for loading cleaned documents as vectors."""
    _LOGGER.info(f"Loading {len(documents)} into the vector database.")
    # todo
    return True
