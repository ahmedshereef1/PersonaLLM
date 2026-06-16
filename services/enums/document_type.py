from enum import StrEnum


class DataCategory(StrEnum):
    REPOSITORIES = "repositories"
    POSTS = "posts"
    ARTICLES = "articles"

    QUERIES = "queries"
    PROMPT = "prompt"

    INSTRUCT_DATASET_SAMPLES = "instruct_dataset_samples"
    INSTRUCT_DATASET = "instruct_dataset"
    PREFERENCE_DATASET_SAMPLES = "preference_dataset_samples"
    PREFERENCE_DATASET = "preference_dataset"
