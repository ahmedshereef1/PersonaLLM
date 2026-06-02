from .base import NoSQLBaseDocument
from ..enums.document_type import DataCategory

from abc import ABC
from pydantic import UUID4, Field

from typing import Optional


class UserDocument(NoSQLBaseDocument):
    first_name: str
    last_name: str

    class Settings:
        name = "users"

    @property
    def user_name(self):
        return f"{self.first_name} {self.last_name}"


# Custom article
class Document(NoSQLBaseDocument, ABC):
    content: dict
    platform: str
    author_id: UUID4 = Field(alias="author_id")
    author_user_name: str = Field(alias="author_user_name")


# Github
class RepositoryDocument(Document):
    name: str
    link: str

    class Settings:
        name = DataCategory.REPOSITORIES


# LinkedIn
class PostDocument(Document):
    image: Optional[str] = None
    link: str | None = None

    class Settings:
        name = DataCategory.POSTS


# Medium
class ArticleDocument(Document):
    link: str

    class Settings:
        name = DataCategory.ARTICLES
