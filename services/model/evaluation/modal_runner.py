from pathlib import Path
import os
import subprocess

from huggingface_hub import HfApi
from loguru import logger

from services.settings import settings

evaluation_dir = Path(__file__).resolve().parent
evaluation_script = evaluation_dir / "evaluate.py"


def run_evaluation(is_dummy: bool = True) -> None:
    assert settings.HUGGINGFACE_ACCESS_TOKEN, "Hugging Face access token is required."
    assert settings.OPENAI_API_KEY, "OpenAI API key is required."

    api = HfApi(token=settings.HUGGINGFACE_ACCESS_TOKEN)
    huggingface_user = api.whoami()["name"]

    logger.info(f"Current Hugging Face user: {huggingface_user}")

    env = os.environ.copy()

    env.update(
        {
            "HUGGINGFACE_ACCESS_TOKEN": settings.HUGGINGFACE_ACCESS_TOKEN,
            "HUGGING_FACE_HUB_TOKEN": settings.HUGGINGFACE_ACCESS_TOKEN,
            "OPENAI_API_KEY": settings.OPENAI_API_KEY,
            "DATASET_HUGGINGFACE_WORKSPACE": huggingface_user,
            "MODEL_HUGGINGFACE_WORKSPACE": huggingface_user,
            "IS_DUMMY": str(is_dummy),
        }
    )

    if getattr(settings, "CLAUDE_API_KEY_ANTI", None):
        env["CLAUDE_API_KEY_ANTI"] = settings.CLAUDE_API_KEY_ANTI

    if getattr(settings, "CLAUDE_BASE_URL", None):
        env["CLAUDE_BASE_URL"] = settings.CLAUDE_BASE_URL

    if getattr(settings, "CLAUDE_MODEL_ID", None):
        env["CLAUDE_MODEL_ID"] = settings.CLAUDE_MODEL_ID

    logger.info("Starting evaluation...")

    subprocess.run(
        ["python", str(evaluation_script)],
        env=env,
        check=True,
    )

    logger.success("Evaluation finished successfully.")
