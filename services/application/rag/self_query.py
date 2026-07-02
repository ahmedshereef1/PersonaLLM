from loguru import logger
import opik
from langchain_anthropic import ChatAnthropic

from services.domain.queries import Query
from .rag_base import RAGStep
from services.settings import settings
from .prompt_template import SelfQueryTemplate

from services.domain.documents import UserDocument
from services.application.utils import split_user_name


class SelfQuery(RAGStep):
    @opik.track(name="SelfQuery.generate")
    def generate(self, query: Query) -> Query:
        if self._mock:
            return query

        prompt = SelfQueryTemplate().create_template()
        model = model = ChatAnthropic(
            model_name=settings.CLAUDE_MODEL_ID,
            api_key=settings.CLAUDE_API_KEY_ANTI,
            base_url=settings.CLAUDE_BASE_URL,
            temperature=0,
        )

        chain = prompt | model

        response = chain.invoke({"question": query})
        user_full_name = response.content.strip("\n ")

        if user_full_name == "none":
            return query

        first_name, last_name = split_user_name(user_full_name)
        user = UserDocument.get_or_create(first_name=first_name, last_name=last_name)

        query.author_id = user.id
        query.author_user_name = user.author_user_name

        return query


if __name__ == "__main__":
    query = Query.from_str(
        "I am Paul Iusztin. Write an article about the best types of advanced RAG methods."
    )
    self_query = SelfQuery()
    query = self_query.generate(query)
    logger.info(f"Extracted author_id: {query.author_id}")
    logger.info(f"Extracted author_full_name: {query.author_full_name}")
