from loguru import logger
from urllib.parse import urlparse

from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers.html2text import Html2TextTransformer

from services.domain.documents import ArticleDocument
from .base_selenium_crawler import BaseCrawler


class CustomArticleCrawler(BaseCrawler):
    model = ArticleDocument

    def __init__(self) -> None:
        super().__init__()

    def extract(self, link: str, **kwargs) -> None:
        old_model = self.model.find(link=link)
        if old_model is not None:
            logger.info(f"Article already exists in the database: {link}")

            return

        logger.info(f"Start scrapping article: {link}")

        loader = AsyncHtmlLoader([link])
        docs = loader.load()

        html2text = Html2TextTransformer()
        docs_transformed = html2text.atransform_documents(docs)
        doc_transformed = docs_transformed[0]

        content = {
            "Tilte": doc_transformed.metadata.get("title"),
            "Description": doc_transformed.metadata.get("description"),
            "Content": doc_transformed.page_content,
            "language": doc_transformed.metadata.get("language"),
        }

        parse_url = urlparse(link)
        platfrom = parse_url.netloc

        user = kwargs["user"]
        instance = self.model(
            content=content,
            link=link,
            platfrom=platfrom,
            author_id=user.id,
            author_user_name=user.author_user_name,
        )
        instance.save()

        logger.info(f"Finished scrapping custom article: {link}")
