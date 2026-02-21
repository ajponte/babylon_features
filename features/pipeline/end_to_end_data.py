# pylint: disable=unused-variable
# pylint: disable=unused-argument
"""Pipeline step to run e2e data pipeline."""
from zenml import pipeline

from features.logger import get_logger
from features.pipeline import generate_datasets

_LOGGER = get_logger()


@pipeline
def end_to_end_data(
    text_split_size: float = 0.1,
    push_to_hugging_face: bool = False,
    dataset_id: str | None = None,
    mock: bool = False,
) -> None:
    """Entry point to run the e22 data pipeline."""
    # todo
    _LOGGER.info("Invoking End to End Data Pipeline")
    wait_for_ids = []

    generate_datasets()
