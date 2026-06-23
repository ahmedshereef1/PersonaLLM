from abc import ABC, abstractmethod

import tiktoken

# from anthropic import Anthropic
from loguru import logger

# from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.fake import FakeListLLM
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from openai import APIConnectionError

# from langchain_anthropic import ChatAnthropic
# from langchain_groq import ChatGroq
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from services import domain
from services.domain.dataset import DatasetType, TrainTestSplit
from services.domain.cleaned_documents import CleanedDocument
from services.domain.prompt import Prompt, GenerateDatasetSamplesPrompt
from services.enums.document_type import DataCategory
from services.application.dataset import constants
from services.application.dataset import generation_utils
from services.application.utils import misc
from .output_parsers import ListPydanticOutputParser
from services.settings import settings

# client = Anthropic(api_key=settings.CLAUDE_API_KEY)


class DatasetGenerator(ABC):
    tokenizer = tiktoken.get_encoding("cl100k_base")
    dataset_type: DatasetType | None = None

    system_prompt_template = """You are a helpful assistant who generates {dataset_format} based on the given context. \
Provide your response in JSON format.
"""
    prompt_template_str: str | None = None

    @classmethod
    def get_system_prompt(cls) -> Prompt:
        assert (
            cls.dataset_type is not None
        ), "Dataset type must be set before calling get_system_prompt()"

        dataset_format = (
            "instruction-answer pairs"
            if cls.dataset_type == DatasetType.INSTRUCTION
            else "instruction-answer triples"
        )

        input_variables = {
            "dataset_format": dataset_format,
        }

        system_prompt = cls.system_prompt_template.format(**input_variables)

        return Prompt(
            template=cls.system_prompt_template,
            input_variables=input_variables,
            content=system_prompt,
        )

    @classmethod
    def get_prompts(
        cls, documents: list[CleanedDocument]
    ) -> dict[DataCategory, list[GenerateDatasetSamplesPrompt]]:
        documents = generation_utils.extract_substring(documents)

        grouped_prompts = {}
        grouped_cleanded_documents = CleanedDocument.group_by_category(documents)
        for category, category_documents in grouped_cleanded_documents.items():
            category_prompt = [
                cls.get_prompt(document) for document in category_documents
            ]
            grouped_prompts[category] = category_prompt

        return grouped_prompts

    @classmethod
    def get_prompt(cls, document: CleanedDocument) -> GenerateDatasetSamplesPrompt:
        assert (
            cls.prompt_template_str is not None
        ), "Prompt template must be set before calling get_prompt()"

        data_category = document.get_category()

        prompt_template = PromptTemplate.from_template(
            template=cls.prompt_template_str,
            template_format="jinja2",
        )
        input_variables = {"extract": document.content}
        prompt = prompt_template.format(**input_variables)
        prompt_tokens = cls.tokenizer.encode(prompt)
        if len(prompt_tokens) > settings.MODEL_MAX_TOKEN_WINDOW:
            prompt_tokens = prompt_tokens[: settings.MODEL_MAX_TOKEN_WINDOW]
            prompt = cls.tokenizer.decode(prompt_tokens)

        prompt = GenerateDatasetSamplesPrompt(
            template=prompt_template.template,
            input_variables=input_variables,
            content=prompt,
            num_tokens=len(prompt_tokens),
            data_category=data_category,
            document=document,
        )

        return prompt

    @classmethod
    def generate(
        cls,
        prompts: dict[DataCategory, list[GenerateDatasetSamplesPrompt]],
        test_size: float = 0.2,
        mock: bool = False,
    ) -> TrainTestSplit:
        assert (
            cls.dataset_type is not None
        ), "Dataset type must be set before calling generate()"

        def _to_langchain(
            prompt: GenerateDatasetSamplesPrompt,
        ) -> list[BaseMessage]:
            messages = [
                SystemMessage(content=cls.get_system_prompt().content),
                HumanMessage(content=prompt.content),
            ]

            return messages

        if mock:
            llm = FakeListLLM(
                responses=[constants.get_mocked_response(cls.dataset_type)]
            )
        else:
            llm = ChatOpenAI(
                model=settings.CLAUDE_MODEL_ID,
                api_key=settings.CLAUDE_API_KEY_ANTI,
                base_url="http://127.0.0.1:8045/v1",
                max_tokens=2000 if cls.dataset_type == DatasetType.PREFERENCE else 1200,
                temperature=0.2,
            )
        parser = ListPydanticOutputParser(
            pydantic_object=cls._get_dataset_sample_type()
        )

        chain = llm | parser

        datasets = {}
        for category, category_prompts in prompts.items():
            print(category, len(category_prompts))
            langchain_category_prompts = [
                _to_langchain(prompt) for prompt in category_prompts
            ]
            batches = misc.batch(langchain_category_prompts, size=15)

            flattened_instruct_dataset_samples = []
            for batch in batches:
                try:
                    config = RunnableConfig(max_concurrency=1)
                    batched_dataset_sample = chain.batch(
                        batch,
                        config=config,
                        stop=None,
                    )

                    for instruct_dataset_sample_batch in batched_dataset_sample:
                        if not instruct_dataset_sample_batch:
                            logger.warning("Received empty batch")
                            continue

                        logger.info(
                            f"Received {len(instruct_dataset_sample_batch)} samples"
                        )

                        flattened_instruct_dataset_samples.extend(
                            instruct_dataset_sample_batch
                        )
                except APIConnectionError as e:
                    logger.error(f"Connection error for category {category}: {e}")
                    continue
                except Exception as e:
                    logger.exception(f"Failed batch for category {category}: {e}")
                    continue
            dataset = domain.dataset.build_dataset(
                dataset_type=cls.dataset_type,
                category=category,
                samples=flattened_instruct_dataset_samples,
            )
            datasets[category] = dataset
            logger.info(
                f"Generated {len(dataset.samples)} samples for category '{category}'."
            )

        processed_datasets = cls.post_process_datasets(datasets, test_size=test_size)

        return processed_datasets

    @classmethod
    def _get_dataset_sample_type(
        cls,
    ) -> (
        type[domain.dataset.InstructDatasetSample]
        | type[domain.dataset.PerferenceDatasetSample]
    ):
        return (
            domain.dataset.InstructDatasetSample
            if cls.dataset_type == DatasetType.INSTRUCTION
            else domain.dataset.PerferenceDatasetSample
        )

    @classmethod
    @abstractmethod
    def post_process_datasets(
        cls,
        datasets: dict[DataCategory, domain.dataset.InstructDataset],
        test_size: float,
    ) -> TrainTestSplit:
        pass


# =========================================================


class InstructionDatasetGenerator(DatasetGenerator):
    dataset_type = DatasetType.INSTRUCTION

    prompt_template_str = """Based on the following extract, generate five instruction-answer pairs. Each instruction \
must ask to write about a specific topic contained in the context. Each answer \
must provide a relevant paragraph based on the information found in the \
context. Only use concepts from the context to generate the instructions. \
Instructions must never explicitly mention a context, a system, a course, or an extract. \
Instructions must be self-contained and general. \
Answers must imitate the writing style of the context. \
    
Example instruction: Explain the concept of an LLM Twin. \
Example answer: An LLM Twin is essentially an AI character that mimics your writing style, personality, and voice. \
It's designed to write just like you by incorporating these elements into a language model. \
The idea is to create a digital replica of your writing habits using advanced AI techniques. \

Structure the answer in JSON format, ready to be loaded in Python by json.loads(), as a list of objects.
Do not add any extra characters and provide your response in JSON format with the following structure:
[
    {"instruction": "...", "answer": "..."},
    ...
]

Extract:
{{extract}}
"""

    @classmethod
    def post_process_datasets(
        cls,
        datasets: dict[DataCategory, domain.dataset.InstructDataset],
        test_size: float,
    ) -> TrainTestSplit:
        train_test_split = generation_utils.create_instruct_train_test_split(
            datasets, test_size=test_size, random_state=42
        )

        return train_test_split


class PreferenceDatasetGenerator(DatasetGenerator):
    dataset_type = DatasetType.PREFERENCE

    prompt_template_str = """Based on the following extract, generate five instruction-answer triples. Each triple should consist of:
1. An instruction asking about a specific topic in the context.
2. A generated answer that attempts to answer the instruction based on the context, named as 'rejected'.
3. An extracted answer that is a relevant excerpt directly from the given context, named as 'chosen'.

Instructions must be self-contained and general, without explicitly mentioning a context, system, course, or extract.

Important:
- Ensure that the extracted answer, the chosen one, is a verbatim copy from the context, including all punctuation and apostrophes.
- Do not add any ellipsis (...) or [...]  to indicate skipped text in the extracted answer.
- If the relevant text is not continuous, use two separate sentences from the context instead of skipping text.

Structure the answer in JSON format, ready to be loaded in Python by json.loads(), as a list of objects.
Do not add any extra characters and provide your response in JSON format with the following structure:
[
    {
        "instruction": "...",
        "rejected": "...",
        "chosen": "..."
    },
    ...
]

Extract:
{{extract}}
"""

    @classmethod
    def post_process_datasets(
        cls,
        datasets: dict[DataCategory, domain.dataset.PerferenceDataset],
        test_size: float,
    ) -> TrainTestSplit:
        datasets = generation_utils.filter_short_answers(data=datasets)
        datasets = generation_utils.filter_answer_format(data=datasets)

        remaining_samples = sum([dataset.num_samples for dataset in datasets.values()])
        logger.info(
            f"Filtered out short answers and answers with incorrect format. Remaining samples: {remaining_samples}"
        )

        train_test_split = generation_utils.create_preference_train_test_split(
            datasets, test_size=test_size, random_state=42
        )

        return train_test_split


def get_dataset_generator(data_type: DatasetType) -> type[DatasetGenerator]:
    if data_type == DatasetType.INSTRUCTION:
        return InstructionDatasetGenerator
    elif data_type == DatasetType.PREFERENCE:
        return PreferenceDatasetGenerator
    else:
        raise ValueError(f"Invalid dataset type: {data_type}")
