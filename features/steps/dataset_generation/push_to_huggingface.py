"""Pipeline step for pushing a generated dataset to Huggingface."""

from typing_extensions import Annotated
from zenml import step

from features.domain.dataset import InstructTrainTestSplit, PreferenceTrainTestSplit
from features.logger import get_logger

_LOGGER = get_logger()


@step
def push_to_hugging_face(
    dataset: Annotated[
        InstructTrainTestSplit | PreferenceTrainTestSplit, "dataset_split"
    ],
    dataset_id: Annotated[str, "dataset_id"],
    huggingface_token,
) -> None:
    """Entry point for pushing a generated dataset to HuggingFace."""
    assert (
        dataset_id is not None
    ), "Dataset ID must be present for pushing to HuggingFace"
    _LOGGER.info(f"Pushing dataset {dataset_id} to HuggingFace.")

    huggingface_dataset = dataset.to_huggingface(flatten=True)
    huggingface_dataset.push_to_hub(dataset_id, token=huggingface_token)
