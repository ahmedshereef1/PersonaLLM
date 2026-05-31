from typing_extensions import Annotated

from services.domain.documents import UserDocument


def crawl_links(
    user: UserDocument, links: list[str]
) -> Annotated[list[str], "crawl_links"]:
    pass
