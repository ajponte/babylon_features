# pylint: disable=too-few-public-methods
"""Represents a prompt for Babylon."""

from features.domain.base.vector import BabylonVectorBasedDocument
from features.domain.cleaned_documents import CleanedDocument
from features.domain.data_category import DataCategory


class Prompt(BabylonVectorBasedDocument):
    """Represents an embedded Prompt document."""
    template: str
    input_variables: dict
    content: str
    num_tokens: int | None = None

    class Config:
        """Prompt document config."""
        category = DataCategory.PROMPT


class GenerateDatasetSamplesPrompt(Prompt):
    """Represents an dataset samples Prompt document."""
    data_category: DataCategory
    document: CleanedDocument
