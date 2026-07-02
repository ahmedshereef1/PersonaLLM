from loguru import logger
import opik
from langchain_anthropic import ChatAnthropic

from services.domain.queries import Query
from .rag_base import RAGStep
from services.settings import settings
from .prompt_template import QueryExpansionTemplate


class QueryExpansion(RAGStep):
    @opik.track(name="QueryExpansion.generate")
    def generate(self, query: Query, expand_to_n: int) -> list[Query]:
        assert (
            expand_to_n > 0
        ), f"'expand_to_n' should be greater than 0. Got {expand_to_n}."

        if self._mock:
            return [query for _ in range(expand_to_n)]

        query_expansion_template = QueryExpansionTemplate()
        prompt = query_expansion_template.create_template(expand_to_n - 1)
        model = ChatAnthropic(
            model_name=settings.CLAUDE_MODEL_ID,
            api_key=settings.CLAUDE_API_KEY_ANTI,
            base_url=settings.CLAUDE_BASE_URL,
            temperature=0.1,
        )

        chain = prompt | model

        response = chain.invoke({"question": query})
        result = response.content

        queries_content = result.strip().split(query_expansion_template.separator)

        queries = [query]
        queries += [
            query.replace_content(stripped_content)
            for content in queries_content
            if (stripped_content := content.strip())
        ]

        return queries


if __name__ == "__main__":
    query = Query.form_str(
        "Write an article about the best types of advanced RAG methods."
    )
    query_expander = QueryExpansion()
    expanded_queries = query_expander.generate(query, expand_to_n=3)
    for expanded_query in expanded_queries:
        logger.info(expanded_query.content)
