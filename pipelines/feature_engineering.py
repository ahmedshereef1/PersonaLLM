from zenml import pipeline

from scripts import feature_engineering as fe_steps


@pipeline
def feature_engineering(
    user_name: list[str], wait_for: str | list[str] | None = None
) -> list[str]:
    raw_documents = fe_steps.query_data_warehouse(user_name, after=wait_for)

    cleaned_documents = fe_steps.clean_documents(raw_documents)
    last_step_cleaned = fe_steps.load_to_vector_db(cleaned_documents)

    embedded_documents = fe_steps.rag_by_chunk_and_embed(cleaned_documents)
    last_step_embedded = fe_steps.load_to_vector_db(embedded_documents)

    return [last_step_cleaned.invocation_id, last_step_embedded.invocation_id]
