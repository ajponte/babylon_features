"""Represents a prompt for Babylon."""
from typing_extensions import Any

from features.domain.base.vector import BabylonVectorBasedDocument
from features.domain.cleaned_documents import CleanedDocument
from features.domain.data_category import DataCategory

class Prompt(BabylonVectorBasedDocument):
    template: str
    input_variables: dict
    content: str
    num_tokens: int | None = None

    class Config:
        category = DataCategory.PROMPT

class GenerateDatasetSamplesPrompt(Prompt):
    data_category: DataCategory
    document: CleanedDocument