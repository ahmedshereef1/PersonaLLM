from opik import track

from services.network.embeddings import CrossEncoderModelSingleton
from services.domain.embedded_chunks import EmbeddedChunk
from services.domain.queries import Query

from .rag_base import RAGStep


class Reranker(RAGStep):
    def __init__(self, mock: bool = False) -> None:
        super().__init__(mock=mock)

        self.model = CrossEncoderModelSingleton()

    @track(name="Reranker.generate")
    def generate(
        self, query: Query, chunks: list[EmbeddedChunk], keep_top_k: int
    ) -> list[EmbeddedChunk]:
        if self._mock:
            return query

        query_doc_tuples = [(query.content, chunk.content) for chunk in chunks]
        scores = self.model(query_doc_tuples)

        scored_query_doc_tuples = list(zip(scores, chunks, strict=False))
        scored_query_doc_tuples.sort(key=lambda x: x[0], reverse=True)

        reranked_documents = scored_query_doc_tuples[:keep_top_k]
        reranked_documents = [doc for _, doc in reranked_documents]

        return reranked_documents
