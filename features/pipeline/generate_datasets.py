# pylint: disable=unused-variable
# pylint: disable=unused-argument
"""Pipeline step to generate datasets for the e2e data pipeline."""
from zenml import pipeline

from features.domain.dataset import DatasetType
from features.steps import dataset_generation as cd_steps
from features.logger import get_logger

_LOGGER = get_logger()
@pipeline
def dataset_generation(
    dataset_type: DatasetType = DatasetType.INSTRUCTION,
    test_split_size: float = 0.1,
    push_to_hugging_face: bool = False,
    mock: bool = False,
    wait_for: str | list[str] | None = None
) -> None:
    """Entry point for generating datasets."""
    _LOGGER.info("Invoking Generate Datasets Pipeline.")
    cleaned_documents = cd_steps