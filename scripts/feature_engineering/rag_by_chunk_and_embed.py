from typing_extensions import Annotated
from zenml import step, get_step_context
from loguru import logger

from services.domain.chunks import Chunk
from services.domain.embedded_chunks import EmbeddedChunk
from services.application.preprocessing import ChunkingDispatcher, EmbeddingDispatcher
from services.application import utils


@step
def rag_by_chunk_and_embed(
    cleaned_documents: Annotated[list, "cleaned_documents"],
) -> Annotated[list, "embedded_documents"]:
    logger.info(f"Received cleaned_documents: {len(cleaned_documents)}")

    metadata = {
        "chunking": {},
        "embedding": {},
        "num_documents": len(cleaned_documents),
    }

    embedded_chunks = []
    for document in cleaned_documents:
        chunks = ChunkingDispatcher.dispatch(document)
        logger.info(f"Generated chunks: {len(chunks)}")

        metadata["chunking"] = _add_chunks_metadata(chunks, metadata["chunking"])

        for batched_chunks in utils.misc.batch(chunks, 10):
            batched_embedded_chunks = EmbeddingDispatcher.dispatch(batched_chunks)
            embedded_chunks.extend(batched_embedded_chunks)

    logger.info(f"Generated embedded_chunks: {len(embedded_chunks)}")

    metadata["embedding"] = _add_embeddings_metadata(
        embedded_chunks, metadata["embedding"]
    )
    metadata["num_chunks"] = len(embedded_chunks)
    metadata["num_embedded_chunks"] = len(embedded_chunks)

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="embedded_documents", metadata=metadata
    )

    return embedded_chunks


def _add_chunks_metadata(chunks: list[Chunk], metadata: dict) -> dict:
    for chunk in chunks:
        category = chunk.get_category()
        if category not in metadata:
            metadata[category] = chunk.metadata
        if "authors" not in metadata[category]:
            metadata[category]["authors"] = list()

        metadata[category]["num_chunks"] = metadata[category].get("num_chunks", 0) + 1
        metadata[category]["authors"].append(chunk.author_user_name)

    for value in metadata.values():
        if isinstance(value, dict) and "authors" in value:
            value["authors"] = list(set(value["authors"]))

    return metadata


def _add_embeddings_metadata(
    embedded_chunks: list[EmbeddedChunk], metadata: dict
) -> dict:
    for embedded_chunk in embedded_chunks:
        category = embedded_chunk.get_category()
        if category not in metadata:
            metadata[category] = embedded_chunk.metadata
        if "authors" not in metadata[category]:
            metadata[category]["authors"] = list()

        metadata[category]["authors"].append(embedded_chunk.author_user_name)

    for value in metadata.values():
        if isinstance(value, dict) and "authors" in value:
            value["authors"] = list(set(value["authors"]))

    return metadata
