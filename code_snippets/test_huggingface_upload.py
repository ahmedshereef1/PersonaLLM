from datasets import Dataset, DatasetDict
from services.settings import settings


def main():
    assert (
        settings.HUGGINGFACE_ACCESS_TOKEN is not None
    ), "HUGGINGFACE_ACCESS_TOKEN is missing"

    train = Dataset.from_dict(
        {
            "instruction": ["What is Python?"],
            "output": ["Python is a programming language."],
        }
    )

    test = Dataset.from_dict(
        {
            "instruction": ["What is AI?"],
            "output": ["Artificial Intelligence."],
        }
    )

    dataset = DatasetDict(
        {
            "train": train,
            "test": test,
        }
    )

    print(dataset)

    dataset.push_to_hub(
        repo_id="AhmedSherif22/test-dataset",
        token=settings.HUGGINGFACE_ACCESS_TOKEN,
    )

    print("✅ Upload successful")


if __name__ == "__main__":
    main()
