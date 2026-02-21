"""Pipeline for generating the instruction dataset."""

from typing_extensions import Annotated, Any
from zenml import ArtifactConfig, get_step_context, step

from features.domain.data_category import DataCategory
from features.domain.dataset import InstructTrainTestSplit
from features.domain.prompt import GenerateDatasetSamplesPrompt
from features.logger import get_logger

_LOGGER = get_logger()


@step
def generate_instruction_dataset(
    prompts: Annotated[
        dict[DataCategory, list[GenerateDatasetSamplesPrompt]], "prompts"
    ],
    test_split_size: Annotated[float, "test_split_size"],
    mock: Annotated[bool, "mock_generation"] = False,
) -> Annotated[
    InstructTrainTestSplit,
    ArtifactConfig(name="instruct_datasets", tags=["dataset", "instruct", "cleaned"]),
]:
    """Entry point for creating instruct datasets."""
    _LOGGER.info("Starting Instruct Dataset Generation.")
