from loguru import logger

from sagemaker.enums import EndpointType
from sagemaker.huggingface import get_huggingface_llm_image_uri

from services.settings import settings
from .config import huggingface_deploy_config, model_resource_config
from .utils import ResouceManager
from .sagemaker_huggingface import DeploymentService, SagemakerHuggingfaceStrategy


def create_endpoint(endpoint_type=EndpointType.INFERENCE_COMPONENT_BASED) -> None:
    assert (
        settings.AWS_ARN_ROLE is not None
    ), "AWS_ARN_ROLE is not set in the .env file."

    logger.info(
        f"Creating endpoint with endpoint_type = {endpoint_type} and model_id = {settings.HF_MODEL_ID}"
    )

    llm_image = get_huggingface_llm_image_uri("huggingface", version="2.2.0")

    resource_manger = ResouceManager()
    deployment_service = DeploymentService(resource_manger=resource_manger)

    SagemakerHuggingfaceStrategy(deployment_service).deploy(
        role_arn=settings.AWS_ARN_ROLE,
        llm_image=llm_image,
        config=huggingface_deploy_config,
        endpoint_name=settings.SAGEMAKER_ENDPOINT_INFERENCE,
        endpoint_config_name=settings.SAGEMAKER_ENDPOINT_CONFIG_INFERENCE,
        gpu_instance_type=settings.GPU_INSTANCE_TYPE,
        resources=model_resource_config,
        endpoint_type=endpoint_type,
    )


if __name__ == "__main__":
    create_endpoint(endpoint_type=EndpointType.MODEL_BASED)
