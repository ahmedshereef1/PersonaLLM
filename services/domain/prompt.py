from services.enums.document_type import DataCategory
from services.domain.base import VectorBaseDocument
from services.domain.cleaned_documents import CleanedDocument


class Prompt(VectorBaseDocument):
    template: str
    input_variables: dict
    content: str
    num_tokens: int | None = None

    class Config:
        category = DataCategory.PROMPT


class GenerateDatasetSamplesPrompt(Prompt):
    data_category: DataCategory
    document: CleanedDocument
