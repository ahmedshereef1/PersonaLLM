import sagemaker

from sagemaker.huggingface import (
    HuggingFaceModel,
    get_huggingface_llm_image_uri,
)

from services.settings import settings


def deploy() -> None:
    session = sagemaker.Session()

    image_uri = get_huggingface_llm_image_uri(
        backend="huggingface",
        region=settings.AWS_REGION,
    )

    hub = {
        "HF_MODEL_ID": settings.HF_MODEL_ID,
        "SM_NUM_GPUS": str(settings.SM_NUM_GPUS),
        "MAX_INPUT_LENGTH": str(settings.MAX_INPUT_LENGTH),
        "MAX_TOTAL_TOKENS": str(settings.MAX_TOTAL_TOKENS),
        "MAX_BATCH_TOTAL_TOKENS": str(settings.MAX_BATCH_TOTAL_TOKENS),
    }

    model = HuggingFaceModel(
        role=settings.AWS_ARN_ROLE,
        image_uri=image_uri,
        env=hub,
        sagemaker_session=session,
    )

    print("Deploying model to SageMaker...")
    print(f"Model: {settings.HF_MODEL_ID}")
    print(f"Endpoint: {settings.SAGEMAKER_ENDPOINT_INFERENCE}")
    print(f"Instance: {settings.GPU_INSTANCE_TYPE}")

    model.deploy(
        initial_instance_count=settings.COPIES,
        instance_type=settings.GPU_INSTANCE_TYPE,
        endpoint_name=settings.SAGEMAKER_ENDPOINT_INFERENCE,
        container_startup_health_check_timeout=900,
    )

    print("Deployment completed!")
    print(f"Endpoint: " f"{settings.SAGEMAKER_ENDPOINT_INFERENCE}")


if __name__ == "__main__":
    deploy()

# to run: uv run --active python -m services.model.inference.deploy_test
