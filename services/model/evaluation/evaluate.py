import concurrent.futures
import gc
import json
import os
import traceback
import time

from datasets import Dataset, load_dataset
from huggingface_hub import HfApi
from huggingface_hub.utils import RepositoryNotFoundError
from openai import OpenAI
from tqdm.auto import tqdm
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from huggingface_hub import hf_hub_download
import pyarrow.parquet as pq

CLAUDE_API_KEY_ANTI = os.environ["CLAUDE_API_KEY_ANTI"]
CLAUDE_BASE_URL = os.environ.get("CLAUDE_BASE_URL", "http://127.0.0.1:8045/v1")
CLAUDE_MODEL_ID = os.environ.get("CLAUDE_MODEL_ID", "claude-sonnet-4-6")
BASE_TOKENIZER_ID = os.environ.get("BASE_TOKENIZER_ID", "unsloth/Llama-3.1-8B")

DATASET_HUGGINGFACE_WORKSPACE = os.environ["DATASET_HUGGINGFACE_WORKSPACE"]
MODEL_HUGGINGFACE_WORKSPACE = os.environ["MODEL_HUGGINGFACE_WORKSPACE"]
HUGGINGFACE_ACCESS_TOKEN = os.environ.get("HUGGINGFACE_ACCESS_TOKEN", "")


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_results_dataset(model_id: str):
    repo_id = f"{DATASET_HUGGINGFACE_WORKSPACE}/{model_id.split('/')[-1]}-results"

    parquet_path = hf_hub_download(
        repo_id=repo_id,
        repo_type="dataset",
        filename="data/test-00000-of-00001.parquet",
        token=HUGGINGFACE_ACCESS_TOKEN,
    )

    table = pq.read_table(parquet_path)
    return Dataset(table)


IS_DUMMY = _parse_bool(os.environ.get("IS_DUMMY", False))

print("====== EVAL PARAMETERS ======")
print(f"{DATASET_HUGGINGFACE_WORKSPACE=}")
print(f"{MODEL_HUGGINGFACE_WORKSPACE=}")
print(f"{IS_DUMMY=}")
print("=============================")


def generate_answers(model_id: str, dataset_name: str):
    def format(sample):
        return "Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n### Instruction:\n{}\n\n### Response:\n".format(
            sample["instruction"]
        )

    dataset = load_dataset(dataset_name, split="test")
    if IS_DUMMY:
        try:
            dataset = dataset.select(range(10))
        except Exception:
            print("Dummy mode active. Failed to trim the dataset to 10 samples.")  # noqa
    print(f"Dataset size: {len(dataset)}")
    dataset = dataset.map(lambda sample: {"prompt": format(sample)})

    print(f"Generating answers for {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_TOKENIZER_ID)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="cuda:0",
    )

    answers = []
    for prompt in dataset["prompt"]:
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            generated_tokens = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.8,
                top_p=0.95,
            )

        answer_tokens = generated_tokens[0][inputs["input_ids"].shape[-1] :]
        answers.append(tokenizer.decode(answer_tokens, skip_special_tokens=True))

    dataset = dataset.add_column("answers", answers)

    print(f"Uploading results for {model_id}")
    dataset.push_to_hub(
        f"{DATASET_HUGGINGFACE_WORKSPACE}/{model_id.split('/')[-1]}-results",
        token=HUGGINGFACE_ACCESS_TOKEN,
    )

    del model
    gc.collect()
    torch.cuda.empty_cache()

    return dataset


# Evaluation (now uses Claude via Antigravity proxy)
def _make_claude_client() -> OpenAI:
    """
    The Antigravity proxy exposes an OpenAI-compatible /v1 endpoint,
    so we can reuse the openai SDK — just point it at the local proxy.
    """
    return OpenAI(
        api_key=CLAUDE_API_KEY_ANTI,
        base_url=CLAUDE_BASE_URL,
    )


def evaluate_answer(instruction: str, answer: str, client: OpenAI) -> dict:
    prompt = f"""You are an expert judge. Please evaluate the quality of a given answer to an instruction based on two criteria:
1. Accuracy: How factually correct is the information presented in the answer? You are a technical expert in this topic.
2. Style: Is the tone and writing style appropriate for a blog post or social media content? It should use simple but technical words and avoid formal or academic language.

Accuracy scale:
1 (Poor): Contains factual errors or misleading information
2 (Good): Mostly accurate with minor errors or omissions
3 (Excellent): Highly accurate and comprehensive

Style scale:
1 (Poor): Too formal, uses some overly complex words
2 (Good): Good balance of technical content and accessibility, but still uses formal words and expressions
3 (Excellent): Perfectly accessible language for blog/social media, uses simple but precise technical terms when necessary

Example of bad style: The Llama2 7B model constitutes a noteworthy progression in the field of artificial intelligence, serving as the successor to its predecessor, the original Llama architecture.
Example of excellent style: Llama2 7B outperforms the original Llama model across multiple benchmarks.

Instruction: {instruction}

Answer: {answer}

Provide your evaluation in JSON format with the following structure:
{{
    "accuracy": {{
        "analysis": "...",
        "score": 0
    }},
    "style": {{
        "analysis": "...",
        "score": 0
    }}
}}
"""

    completion = client.chat.completions.create(
        model=CLAUDE_MODEL_ID,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant who evaluates answers based on accuracy and style. Provide your response in JSON format with a short analysis and score for each criterion.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_tokens=1000,
        temperature=0,
    )

    content = completion.choices[0].message.content

    if isinstance(content, list):
        content = "".join(block.text for block in content if hasattr(block, "text"))

    content = content.strip()

    # Remove markdown fences (```json ... ```)
    if content.startswith("```"):
        lines = content.splitlines()

        # remove first line (```json or ```)
        lines = lines[1:]

        # remove last ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    return json.loads(content)


def evaluate_batch(batch, start_index):
    client = _make_claude_client()
    return [
        (i, evaluate_answer(instr, ans, client))
        for i, (instr, ans) in enumerate(batch, start=start_index)
    ]


def evaluate_answers(
    model_id: str, num_threads: int = 10, batch_size: int = 5
) -> Dataset:
    # Load the dataset
    dataset = _load_results_dataset(model_id)

    # Create batches of instruction-answer pairs with their original indices
    batches = [
        (
            i,
            list(
                zip(
                    dataset["instruction"][i : i + batch_size],
                    dataset["answers"][i : i + batch_size],
                    strict=False,
                )
            ),
        )
        for i in range(0, len(dataset), batch_size)
    ]

    evaluations = [None] * len(dataset)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(evaluate_batch, batch, start_index)
            for start_index, batch in batches
        ]

        for future in tqdm(
            concurrent.futures.as_completed(futures), total=len(futures)
        ):
            for index, evaluation in future.result():
                evaluations[index] = evaluation

    # Replace the 'evaluation' column if it exists, otherwise add it
    if "evaluation" in dataset.column_names:
        dataset = dataset.remove_columns(["evaluation"])
    dataset = dataset.add_column("evaluation", evaluations)

    # Post-process evaluations
    accuracy_scores = []
    style_scores = []

    for evaluation in dataset["evaluation"]:
        try:
            eval_dict = (
                json.loads(evaluation) if isinstance(evaluation, str) else evaluation
            )
            accuracy_score = eval_dict["accuracy"]["score"]
            style_score = eval_dict["style"]["score"]

            accuracy_scores.append(accuracy_score)
            style_scores.append(style_score)

        except (json.JSONDecodeError, KeyError, TypeError):
            # If there's an error, append None to maintain alignment
            accuracy_scores.append(None)
            style_scores.append(None)

    # Add new columns to the dataset
    if "accuracy" in dataset.column_names:
        dataset = dataset.remove_columns(["accuracy"])
    dataset = dataset.add_column("accuracy", accuracy_scores)
    if "style" in dataset.column_names:
        dataset = dataset.remove_columns(["style"])
    dataset = dataset.add_column("style", style_scores)

    repo_id = f"{DATASET_HUGGINGFACE_WORKSPACE}/{model_id.split('/')[-1]}-results"

    api = HfApi(token=HUGGINGFACE_ACCESS_TOKEN)

    # Delete the old repository if it exists
    try:
        api.delete_repo(repo_id=repo_id, repo_type="dataset")
        print(f"Deleted {repo_id}, waiting for deletion to complete...")
        time.sleep(10)  # wait 10 seconds
    except Exception:
        pass

    # Upload the new dataset
    dataset.push_to_hub(
        repo_id,
        token=HUGGINGFACE_ACCESS_TOKEN,
    )

    return dataset


def check_if_huggingface_model_exists(model_id: str, default_value: str) -> str:
    api = HfApi(token=HUGGINGFACE_ACCESS_TOKEN)

    try:
        api.model_info(model_id)
        print(f"Found model on HF: '{model_id}'.")
    except RepositoryNotFoundError:
        print(f"Model '{model_id}' does not exist.")
        model_id = default_value
        print(f"Defaulting to '{model_id}'")
        print("Train your own model to avoid this behavior.")

    return model_id


def check_if_huggingface_dataset_exists(dataset_id: str, default_value: str) -> str:
    api = HfApi(token=HUGGINGFACE_ACCESS_TOKEN)

    try:
        api.dataset_info(dataset_id)
        print(f"Found dataset on HF: '{dataset_id}'.")
    except RepositoryNotFoundError:
        print(f"Dataset '{dataset_id}' does not exist.")
        dataset_id = default_value
        print(f"Defaulting to '{dataset_id}'")
        print("Use a valid dataset or create your own to avoid this behavior.")  # noqa

    return dataset_id


model_ids = [
    check_if_huggingface_model_exists(
        f"{MODEL_HUGGINGFACE_WORKSPACE}/TwinLlama-3.1-8B",
        default_value="AhmedSherif22/TwinLlama-3.1-8B",
    ),
    check_if_huggingface_model_exists(
        f"{MODEL_HUGGINGFACE_WORKSPACE}/TwinLlama-3.1-8B-DPO",
        default_value="AhmedSherif22/TwinLlama-3.1-8B-DPO",
    ),
    "meta-llama/Llama-3.1-8B-Instruct",
]

if __name__ == "__main__":
    try:
        # Run generation
        for model_id in model_ids:
            dataset_name = check_if_huggingface_dataset_exists(
                f"{DATASET_HUGGINGFACE_WORKSPACE}/llmtwin",
                default_value="AhmedSherif22/llmtwin",
            )
            generate_answers(model_id, dataset_name=dataset_name)

        # Run evaluation
        for model_id in model_ids:
            evaluate_answers(model_id)

        # Analyze results
        for model_id in model_ids:
            dataset = _load_results_dataset(model_id)

            score = sum(dataset["accuracy"]) / len(dataset["accuracy"])
            print(f"{model_id.split('/')[-1]} - Accuracy: {score:.2f}")

            score = sum(dataset["style"]) / len(dataset["style"])
            print(f"{model_id.split('/')[-1]} - Style: {score:.2f}")
    except Exception:
        traceback.print_exc()
        raise
