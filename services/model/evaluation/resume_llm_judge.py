import os
import builtins
from tqdm import tqdm
from services.settings import settings

from services.model.evaluation.evaluate import evaluate_answers

# ======================================================
# Environment
# ======================================================
os.environ["CLAUDE_API_KEY_ANTI"] = settings.CLAUDE_API_KEY_ANTI
os.environ["CLAUDE_BASE_URL"] = settings.CLAUDE_BASE_URL
os.environ["CLAUDE_MODEL_ID"] = settings.CLAUDE_MODEL_ID

os.environ["HUGGINGFACE_ACCESS_TOKEN"] = settings.HUGGINGFACE_ACCESS_TOKEN
os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.HUGGINGFACE_ACCESS_TOKEN

# Your HF username/workspace
os.environ["DATASET_HUGGINGFACE_WORKSPACE"] = "AhmedSherif22"
os.environ["MODEL_HUGGINGFACE_WORKSPACE"] = "AhmedSherif22"

# ======================================================
MODELS = [
    "AhmedSherif22/TwinLlama-3.1-8B",
    "AhmedSherif22/TwinLlama-3.1-8B-DPO",
    "meta-llama/Llama-3.1-8B-Instruct",
]

# ======================================================
# Hide only the RAW RESPONSE prints
# ======================================================

_original_print = builtins.print


def filtered_print(*args, **kwargs):
    if not args:
        return

    text = " ".join(str(a) for a in args)

    # Hide only the debugging output you added
    if (
        "RAW RESPONSE" in text
        or text.startswith("'")
        or text.startswith("{'accuracy'")
        or text.startswith('{"accuracy"')
        or text.startswith("{\n")
    ):
        return

    _original_print(*args, **kwargs)


builtins.print = filtered_print

# ======================================================

results = []

print("=" * 80)
print("LLM-as-a-Judge Evaluation")
print("=" * 80)

for model in tqdm(MODELS, desc="Evaluating Models", unit="model"):
    dataset = evaluate_answers(
        model,
        num_threads=2,
        batch_size=5,
    )

    accuracy = sum(dataset["accuracy"]) / len(dataset["accuracy"])
    style = sum(dataset["style"]) / len(dataset["style"])

    results.append((model, accuracy, style))

# Restore normal print
builtins.print = _original_print

print("\n")
print("=" * 80)
print("FINAL RESULTS")
print("=" * 80)

for model, accuracy, style in results:
    print(f"\n{model}")
    print(f"Accuracy : {accuracy:.2f}")
    print(f"Style    : {style:.2f}")

print("\n" + "=" * 80)
print("Evaluation completed successfully.")
print("=" * 80)
