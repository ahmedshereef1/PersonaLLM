from enum import Enum

from services.domain.base import VectorBaseDocument
from services.enums.document_type import DataCategory

from datasets import Dataset, DatasetDict, concatenate_datasets


class DatasetType(Enum):
    INSTRUCTION = "instruction"
    PREFERENCE = "preference"


# Instruction tuning
class InstructDatasetSample(VectorBaseDocument):
    instruction: str
    answer: str

    class Config:
        category = DataCategory.INSTRUCT_DATASET_SAMPLES


# Preference tuning (RLHF/DPO style)
class PerferenceDatasetSample(VectorBaseDocument):
    instruction: str
    rejected: str
    chosen: str

    class Config:
        category = DataCategory.PREFERENCE_DATASET_SAMPLES


# -----------------------------------------------------------
class InstructDataset(VectorBaseDocument):
    category: DataCategory
    samples: list[InstructDatasetSample]

    class Config:
        category = DataCategory.INSTRUCT_DATASET

    @property
    def num_samples(self) -> int:
        return len(self.samples)

    def to_huggingface(self) -> "Dataset":
        data = [sample.model_dump() for sample in self.samples]

        return Dataset.from_dict(
            {
                "instruction": [d["instruction"] for d in data],
                "output": [d["answer"] for d in data],
            }
        )


class TrainTestSplit(VectorBaseDocument):
    train: dict
    test: dict
    test_split_size: float

    def to_huggingface(self, flatten: bool = False) -> "DatasetDict":
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

        return DatasetDict(
            {
                "train": train_datasets,
                "test": test_datasets,
            }
        )


class InstructTrainTestSplit(TrainTestSplit):
    train: dict[DataCategory, InstructDataset]
    test: dict[DataCategory, InstructDataset]
    test_split_size: float

    class Config:
        category = DataCategory.INSTRUCT_DATASET


# -------------------------------------------------------
class PerferenceDataset(VectorBaseDocument):
    category: DataCategory
    samples: list[PerferenceDatasetSample]

    class Config:
        category = DataCategory.PREFERENCE_DATASET

    @property
    def num_samples(self) -> int:
        return len(self.samples)

    def to_huggingface(self) -> "Dataset":
        data = [sample.model_dump() for sample in self.samples]

        return Dataset.from_dict(
            {
                "prompt": [d["instruction"] for d in data],
                "rejected": [d["rejected"] for d in data],
                "chosen": [d["chosen"] for d in data],
            }
        )


class PreferenceTrainTestSplit(TrainTestSplit):
    train: dict[DataCategory, PerferenceDataset]
    test: dict[DataCategory, PerferenceDataset]
    test_split_size: float

    class Config:
        category = DataCategory.PREFERENCE_DATASET


def build_dataset(dataset_type, *args, **kwargs) -> InstructDataset | PerferenceDataset:
    if dataset_type == DatasetType.INSTRUCTION:
        return InstructDataset(*args, **kwargs)
    elif dataset_type == DatasetType.PREFERENCE:
        return PerferenceDataset(*args, **kwargs)
    else:
        raise ValueError(f"Invalid dataset type: {dataset_type}")
