"""Representations for the categories of data the pipeline handles."""

from enum import StrEnum


class DataCategory(StrEnum):
    """Represents the categories of data the pipeline handles."""

    PROMPT = "prompt"
    QUERIES = "queries"

    INSTRUCT_DATASET_SAMPLES = "instruct_dataset_samples"
    INSTRUCT_DATASET = "instruct_dataset"
    PREFERENCE_DATASET_SAMPLES = "preference_dataset_samples"
    PREFERENCE_DATASET = "preference_dataset"

    TRANSACTIONS = "transactions"
