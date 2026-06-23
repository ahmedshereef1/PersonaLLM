from typing import Any

from zenml import step, get_step_context, ArtifactConfig
from typing_extensions import Annotated

from services.domain.dataset import DatasetType, PreferenceTrainTestSplit
from services.enums.document_type import DataCategory
from services.domain.prompt import GenerateDatasetSamplesPrompt
from services.application.dataset import generation


@step
def generate_preference_dataset(
    prompts: Annotated[
        dict[DataCategory, list[GenerateDatasetSamplesPrompt]], "prompts"
    ],
    test_split_size: Annotated[float, "test_split_size"],
    mock: Annotated[bool, "mock_generation"] = False,
) -> Annotated[
    PreferenceTrainTestSplit,
    ArtifactConfig(
        name="preference_datasets",
        tags=["dataset", "preference", "cleaned"],
    ),
]:
    dataset_generator = generation.get_dataset_generator(DatasetType.PREFERENCE)
    datasets = dataset_generator.generate(prompts, test_size=test_split_size, mock=mock)

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="preference_datasets",
        metadata=_get_metadata_preference_dataset(datasets),
    )

    return datasets


def _get_metadata_preference_dataset(
    datasets: PreferenceTrainTestSplit,
) -> dict[str, Any]:
    preference_dataset_categories = list(datasets.train.keys())
    train_num_samples = {
        category: preference_dataset.num_samples
        for category, preference_dataset in datasets.train.items()
    }
    test_num_samples = {
        category: preference_dataset.num_samples
        for category, preference_dataset in datasets.test.items()
    }

    return {
        "data_categories": preference_dataset_categories,
        "test_splot_size": datasets.test_split_size,
        "train_num_samples_per_category": train_num_samples,
        "test_num_samples_per_category": test_num_samples,
    }
