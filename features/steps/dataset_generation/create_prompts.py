# pylint: disable=unused-argument
"""Step for generating prompts."""

from typing_extensions import Annotated

from zenml import step

from features.domain.data_category import DataCategory
from features.domain.dataset import DatasetType
from features.domain.prompt import GenerateDatasetSamplesPrompt


@step
def create_prompts(
    documents: Annotated[list, "queried_cleaned_documents"],
    dataset_type: Annotated[DatasetType, "dataset_type"],
) -> Annotated[dict[DataCategory, list[GenerateDatasetSamplesPrompt]], "prompts"]:
    """Entry point for Prompt Generation Step."""

    # todo
    samples: list[GenerateDatasetSamplesPrompt] = []
    ret: dict[DataCategory, list[GenerateDatasetSamplesPrompt]] = {}
    ret.update({DataCategory.PROMPT: samples})
    return ret
