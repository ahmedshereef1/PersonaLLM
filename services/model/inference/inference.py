from typing import Optional, Dict, Any
from loguru import logger
import json

import boto3

from services.domain.inference import Inference
from services.settings import settings


class LLMInferenceSagemakerEndpoint(Inference):
    """
    Class for performing inference using a SageMaker endpoint for LLM schemas.
    """

    def __init__(
        self,
        endpoint_name: str,
        default_payload: Optional[Dict[str, Any]] = None,
        inference_component_name: Optional[str] = None,
    ) -> None:
        super().__init__()

        self.client = boto3.client(
            "sagemaker-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
        )
        self.endpoint_name = endpoint_name
        self.payload = default_payload if default_payload else self._default_payload()
        self.inference_component_name = inference_component_name

    def _default_payload(self) -> Dict[str, Any]:
        """
        Generates the default payload for the inference request.

        Returns:
            dict: The default payload.
        """
        return {
            "inputs": "How is the FIFA world cup 2026?",
            "parameters": {
                "max_new_tokens": settings.MAX_NEW_TOKENS_INFERENCE,
                "top_p": settings.TOP_P_INFERENCE,
                "temperature": settings.TEMPERATURE_INFERENCE,
                "return_full_text": False,
            },
        }

    def set_payload(
        self, inputs: str, parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Sets the payload for the inference request.

        Args:
            inputs (str): The input text for the inference.
            parameters (dict, optional): Additional parameters for the inference. Defaults to None.
        """
        self.payload["inputs"] = inputs
        if parameters:
            self.payload["parameters"].update(parameters)

    def inference(self) -> Dict[str, Any]:
        """
        Performs the inference request using the SageMaker endpoint.

        Returns:
            dict: The response from the inference request.
        Raises:
            Exception: If an error occurs during the inference request.
        """

        try:
            logger.info("Sending inference request to SageMaker...")
            invoke_args = {
                "EndpointName": self.endpoint_name,
                "ContentType": "application/json",
                "Body": json.dumps(self.payload),
            }
            if self.inference_component_name not in ["None", None]:
                invoke_args["InferenceComponentName"] = self.inference_component_name

            response = self.client.invoke_endpoint(**invoke_args)
            response_body = response["Body"].read().decode("utf8")

            return json.loads(response_body)

        except Exception:
            logger.exception("SageMake inference failed.")
            raise
