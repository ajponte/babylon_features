# pylint: disable=unused-variable
# pylint: disable=unused-argument
"""Step for chunking and embedding cleaned Babylon Data Lake documents into vectors."""

from typing_extensions import Annotated
from zenml import step

from features_pipeline.logger import get_logger

_LOGGER = get_logger()


@step
def chunk_and_embed(
    cleaned_documents: Annotated[list, "cleaned_documents"],
) -> Annotated[list, "embedded_documents"]:
    """Entry point for embedding and chunking previously cleaned documents."""
    metadata = {
        "chunking": {},
        "embedding": {},
        "num_documents": len(cleaned_documents),
    }

    embedded_chunks = []

    # todo
    return embedded_chunks
