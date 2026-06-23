from sklearn.model_selection import train_test_split

from services.domain.cleaned_documents import CleanedDocument
from services.application.preprocessing.operations.chunking import chunk_document
from services.enums.document_type import DataCategory
from services.domain.dataset import (
    InstructDataset,
    PerferenceDataset,
    InstructDatasetSample,
    InstructTrainTestSplit,
    PerferenceDatasetSample,
    PreferenceTrainTestSplit,
)


def create_preference_train_test_split(
    data: dict[DataCategory, PerferenceDataset], test_size=0.2, random_state=42
) -> PreferenceTrainTestSplit:
    train_data = {}
    test_data = {}

    for category, dataset in data.items():
        samples = dataset.samples
        samples_dicts = [sample.model_dump() for sample in samples]

        if len(samples_dicts) > 0:
            train_samples_dicts, test_samples_dicts = train_test_split(
                samples_dicts, test_size=test_size, random_state=random_state
            )
            train_samples = [
                PerferenceDatasetSample(**sample_dict)
                for sample_dict in train_samples_dicts
            ]
            test_samples = [
                PerferenceDatasetSample(**sample_dict)
                for sample_dict in test_samples_dicts
            ]
        else:
            train_samples = []
            test_samples = []

        train_dataset = PerferenceDataset(category=category, samples=train_samples)
        test_dataset = PerferenceDataset(category=category, samples=test_samples)

        train_data[category] = train_dataset
        test_data[category] = test_dataset

    return PreferenceTrainTestSplit(
        train=train_data, test=test_data, test_split_size=test_size
    )


def filter_short_answers(
    data: dict[DataCategory, PerferenceDataset], min_length: int = 100
) -> dict[DataCategory, PerferenceDataset]:
    def is_long_enough(example: PerferenceDatasetSample) -> bool:
        return len(example.chosen) >= min_length and len(example.rejected) >= min_length

    filtered_data = {}
    for category, dataset in data.items():
        filetered_dataset_samples = list(filter(is_long_enough, dataset.samples))
        filtered_dataset = PerferenceDataset(
            category=category,
            samples=filetered_dataset_samples,
        )

        filtered_data[category] = filtered_dataset

    return filtered_data


def filter_answer_format(
    data: dict[DataCategory, PerferenceDataset],
) -> dict[DataCategory, PerferenceDataset]:
    def is_valid_format(example: PerferenceDatasetSample) -> bool:
        chosen = example.chosen

        return len(chosen) > 0 and chosen[0].isupper() and chosen[-1] in (".", "!", "?")

    filtered_data = {}
    for category, dataset in data.items():
        filetered_dataset_samples = list(filter(is_valid_format, dataset.samples))
        filtered_dataset = PerferenceDataset(
            category=category,
            samples=filetered_dataset_samples,
        )

        filtered_data[category] = filtered_dataset

    return filtered_data


def create_instruct_train_test_split(
    data: dict[DataCategory, InstructDataset], test_size=0.2, random_state=42
):
    train_data = {}
    test_data = {}

    for category, dataset in data.items():
        samples = dataset.samples
        samples_dicts = [sample.model_dump() for sample in samples]

        if len(samples_dicts) > 0:
            train_samples_dicts, test_samples_dicts = train_test_split(
                samples_dicts, test_size=test_size, random_state=random_state
            )
            train_samples = [
                InstructDatasetSample(**sample_dict)
                for sample_dict in train_samples_dicts
            ]
            test_samples = [
                InstructDatasetSample(**sample_dict)
                for sample_dict in test_samples_dicts
            ]
        else:
            train_samples = []
            test_samples = []

        train_dataset = InstructDataset(category=category, samples=train_samples)
        test_dataset = InstructDataset(category=category, samples=test_samples)

        train_data[category] = train_dataset
        test_data[category] = test_dataset

    return InstructTrainTestSplit(
        train=train_data, test=test_data, test_split_size=test_size
    )


def extract_substring(
    documents: list[CleanedDocument], min_length: int = 1000, max_length: int = 2000
) -> list[CleanedDocument]:
    extracts = []
    for doc in documents:
        document_extracts = chunk_document(doc.content, min_length, max_length)
        for extract in document_extracts:
            # creates a shallow clone of the original document,
            # preserving all metadata fields (id, source, timestamps, etc.)
            subdocument = doc.model_copy()
            subdocument.content = extract

            extracts.append(subdocument)

    return extracts
