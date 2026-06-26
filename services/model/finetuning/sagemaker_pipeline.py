from pathlib import Path
import subprocess
import sys

from loguru import logger
from huggingface_hub import HfApi

from services.settings import settings

finetuning_dir = Path(__file__).resolve().parent


def run_finetuning_on_sagemaker(
    finetuning_type: str = "sft",
    num_train_epochs: int = 3,
    per_device_train_batch_size: int = 2,
    learning_rate: float = 3e-4,
    dataset_huggingface_workspace: str = "AhmedSherif22",
    is_dummy: bool = False,
):
    api = HfApi()
    user = api.whoami(token=settings.HUGGINGFACE_ACCESS_TOKEN)["name"]

    logger.info(f"Current Hugging Face user: {user}")

    cmd = [
        sys.executable,
        str(finetuning_dir / "finetune.py"),
        "--finetuning_type",
        finetuning_type,
        "--num_train_epochs",
        str(num_train_epochs),
        "--per_device_train_batch_size",
        str(per_device_train_batch_size),
        "--learning_rate",
        str(learning_rate),
        "--dataset_huggingface_workspace",
        dataset_huggingface_workspace,
        "--model_output_huggingface_workspace",
        user,
        "--model_dir",
        "outputs",
        "--output_data_dir",
        "outputs",
        "--n_gpus",
        "1",
    ]

    if is_dummy:
        cmd.extend(["--is_dummy", "True"])

    subprocess.run(cmd, check=True)
