from pydantic_settings import BaseSettings, SettingsConfigDict

from loguru import logger
from zenml.client import Client


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- settings even when working locally. ---

    # OpenAI API
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL_ID: str = "gpt-4o-mini"

    # Calude API
    CLAUDE_API_KEY: str | None = None

    # HuggingFace
    HUGGINGFACE_ACCESS_TOKEN: str | None = None

    # MongoDB database
    MONGO_INITDB_ROOT_USERNAME: str
    MONGO_INITDB_ROOT_PASSWORD: str

    DATABASE_HOST: str
    DATABASE_NAME: str

    # LinkedIn Credentials
    LINKEDIN_USERNAME: str | None = None
    LINKEDIN_PASSWORD: str | None = None

    # RAG
    TEXT_EMBEDDING_MODEL_ID: str
    RERANKING_CROSS_ENCODER_MODEL_ID: str
    RAG_MODEL_DEVICE: str

    # Vector DB (Qdrant)
    USE_QDRANT_CLOUD: bool
    QDRANT_DATABASE_HOST: str
    QDRANT_DATABASE_PORT: int
    QDRANT_CLOUD_URL: str
    QDRANT_APIKEY: str

    # UV
    UV_LINK_MODE: str = "copy"

    @classmethod
    def load_settings(cls) -> "Settings":
        """
        Tries to load settings from the ZenML secret store, if the secrets does not exist, it initializes
        the settings from the .env file with default values.

        Returns:
            Settings: The initialized settings object.
        """
        try:
            logger.info("Loading settings from the ZenML secret store.")

            settings_secrets = Client().get_secret("settings")
            settings = Settings(**settings_secrets.secret_values)
        except (RuntimeError, KeyError):
            logger.warning(
                "Failed to load settings from the ZenML secret store. Defaulting to loading the settings from the '.env' file."
            )

            settings = Settings()
        return settings


settings = Settings.load_settings()
