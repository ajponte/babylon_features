# pylint: disable=too-few-public-methods
"""Dataset definitions."""
from enum import Enum

from datasets import Dataset, DatasetDict, concatenate_datasets

from features.domain.base import BabylonVectorBasedDocument
from features.domain.data_category import DataCategory


class DatasetType(Enum):
    """Represents the types of datasets the pipeline can generate."""
    INSTRUCTION = "instruction"
    PREFERENCE = "preference"


class InstructDataset(BabylonVectorBasedDocument):
    """Represents an instruct dataset."""
    category: DataCategory
    samples: list[BabylonVectorBasedDocument]

    class Config:
        """Config for instruct dataset model."""
        category = DataCategory.INSTRUCT_DATASET

    @property
    def num_samples(self) -> int:
        """Return the number of samples in this dataset."""
        return len(self.samples)

    def to_huggingface(self) -> "Dataset":
        """convert this instruct dataset to a HuggingFace-compatible dataset."""
        data = [sample.model_dump() for sample in self.samples]

        return Dataset.from_dict(
            {
                "instruction": [d["instruction"] for d in data],
                "output": [d["answer"] for d in data],
            }
        )


class TrainTestSplit(BabylonVectorBasedDocument):
    """Represents the training data split by test data."""
    train: dict
    test: dict
    test_split_size: float

    def to_huggingface(self, flatten: bool = False) -> "DatasetDict":
        """Convert this test training data to a HuggingFace-compatible data dictionary."""
        train_datasets = {
            category.value: dataset.to_huggingface()
            for category, dataset in self.train.items()
        }
        test_datasets = {
            category.value: dataset.to_huggingface()
            for category, dataset in self.test.items()
        }

        if flatten:
            train_datasets = concatenate_datasets(list(train_datasets.values()))
            test_datasets = concatenate_datasets(list(test_datasets.values()))
        else:
            train_datasets = Dataset.from_dict(train_datasets)
            test_datasets = Dataset.from_dict(test_datasets)

        return DatasetDict({"train": train_datasets, "test": test_datasets})


class InstructTrainTestSplit(TrainTestSplit):
    """Represents the training dataset split by instruct."""
    train: dict[DataCategory, InstructDataset]
    test: dict[DataCategory, InstructDataset]
    test_split_size: float

    class Config:
        """Config for Instruct Train Split model."""
        category = DataCategory.INSTRUCT_DATASET


class PreferenceDatasetSample(BabylonVectorBasedDocument):
    """Represents a sample from the Preference dataset."""
    instruction: str
    rejected: str
    chosen: str

    class Config:
        """Config for Sample Preference dataset model."""
        category = DataCategory.PREFERENCE_DATASET_SAMPLES


class PreferenceDataset(BabylonVectorBasedDocument):
    """Represents the Preference dataset."""
    category: DataCategory
    samples: list[PreferenceDatasetSample]

    class Config:
        """Config for Preference dataset model."""
        category = DataCategory.PREFERENCE_DATASET

    @property
    def num_samples(self) -> int:
        """Return the number of samples in this dataset."""
        return len(self.samples)

    def to_huggingface(self) -> "Dataset":
        """Concert this model to a HuggingFace-compatible dataset."""
        data = [sample.model_dump() for sample in self.samples]

        return Dataset.from_dict(
            {
                "prompt": [d["instruction"] for d in data],
                "rejected": [d["rejected"] for d in data],
                "chosen": [d["chosen"] for d in data],
            }
        )


class PreferenceTrainTestSplit(TrainTestSplit):
    """Represents the preference training data split by test data."""
    train: dict[DataCategory, PreferenceDataset]
    test: dict[DataCategory, PreferenceDataset]
    test_split_size: float

    class Config:
        """Config for PreferenceTrainTestSplit model."""
        category = DataCategory.PREFERENCE_DATASET
