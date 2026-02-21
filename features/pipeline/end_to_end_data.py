# pylint: disable=unused-variable
# pylint: disable=unused-argument
# pylint: disable=not-callable
"""Pipeline step to run e2e data pipeline."""
from zenml import pipeline

from features.logger import get_logger
from features.pipeline.generate_datasets import generate_datasets

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
    wait_for_ids: list[str] = []

    generate_datasets(  # type: ignore
        test_split_size=text_split_size,
        push_to_hugging_face=push_to_hugging_face,
        dataset_id=dataset_id,
        mock=mock,
        wait_for=wait_for_ids[0] if wait_for_ids else None
    )
