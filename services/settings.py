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

    DATABASE_HOST: str = "mongodb://llm_twin:llm_twin@127.0.0.1:27017"
    DATABASE_NAME: str = "llm_twin"

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
