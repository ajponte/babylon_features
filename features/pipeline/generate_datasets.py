# pylint: disable=unused-variable
# pylint: disable=unused-argument
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=not-callable
# pylint: disable=inconsistent-return-statements
"""Pipeline step to generate datasets for the e2e data pipeline."""

from zenml import pipeline

from features.domain.dataset import DatasetType
from features.steps import dataset_generation as gen_steps
from features.logger import get_logger

_LOGGER = get_logger()


@pipeline
def generate_datasets(
    dataset_type: DatasetType = DatasetType.INSTRUCTION,
    test_split_size: float = 0.1,
    push_to_hugging_face: bool = False,
    dataset_id: str | None = None,
    mock: bool = False,
    wait_for: str | list[str] | None = None,
) -> None:
    """Entry point for generating datasets."""
    _LOGGER.info("Invoking Generate Datasets Pipeline.")
    cleaned_documents = gen_steps.query_feature_store(after=wait_for)  # type: ignore
    prompts = gen_steps.create_prompts(  # type: ignore
        documents=cleaned_documents, dataset_type=dataset_type
    )

    if dataset_type == DatasetType.INSTRUCTION:
        dataset = gen_steps.generate_instruction_dataset(  # type: ignore
            prompts=prompts, test_split_size=test_split_size, mock=mock
        )
    elif dataset_type == DatasetType.PREFERENCE:
        _LOGGER.war(f"{DatasetType.PREFERENCE} not supported yet")
        return None
    else:
        raise ValueError(f"Invalid dataset type: {dataset_type}")

    if push_to_hugging_face:
        gen_steps.push_to_huggingface(dataset=dataset, dataset_id=dataset_id)  # type: ignore
