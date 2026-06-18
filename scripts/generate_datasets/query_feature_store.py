from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger
from qdrant_client.http import exceptions
from typing_extensions import Annotated

from zenml import step

from services.domain.base.nosql import NoSQLBaseDocument
from services.domain.cleaned_documents import (
    CleanedDocument,
    CleanedArticleDocument,
    CleanedPostDocument,
    CleanedRepositoryDocument,
)


@step
def query_feature_store() -> Annotated[list, "queried_cleaned_documents"]:
    logger.info("Quering feature store.")

    result = fetch_all_data()

    cleaned_documents = [doc for query_result in result for doc in query_result]

    return cleaned_documents


def fetch_all_data() -> dict[str, list[NoSQLBaseDocument]]:
    with ThreadPoolExecutor() as executer:
        query = {
            executer.submit(
                __fetch_articles,
            ): "articles",
            executer.submit(
                __fetch_posts,
            ): "posts",
            executer.submit(
                __fetch_repositories,
            ): "repositories",
        }

        results = {}
        for res in as_completed(query):
            query_name = query[res]
            try:
                results[query_name] = res.result()
            except Exception:
                logger.exception(f"'{query_name}' request failed.")

                results[query_name] = []


def __fetch_articles() -> list[CleanedDocument]:
    return __fetch(CleanedArticleDocument)


def __fetch_posts() -> list[CleanedDocument]:
    return __fetch(CleanedPostDocument)


def __fetch_repositories() -> list[CleanedDocument]:
    return __fetch(CleanedRepositoryDocument)


def __fetch(
    clean_document_type: type[CleanedDocument], limit: int = 1
) -> list[CleanedDocument]:
    try:
        cleand_document, next_offset = clean_document_type.bulk_find(limit=limit)
    except exceptions.UnexpectedResponse:
        return []

    while next_offset:
        documents, next_offset = clean_document_type.bulk_find(limit=limit)
        cleand_document.extend(documents)

    return cleand_document
