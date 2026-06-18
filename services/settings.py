from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger
from zenml.client import Client
from zenml.exceptions import EntityExistsError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- settings even when working locally. ---

    # OpenAI API
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL_ID: str = "gpt-4o-mini"
    OPENAI_API_BASE: str = "https://api.goose.ai/v1/engines/gpt-j-6b"

    MODEL_MAX_TOKEN_WINDOW: int = 128_000

    # Calude API
    CLAUDE_API_KEY: str | None = None
    CLAUDE_MODEL_ID: str = "claude-sonnet-4-6"

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

    # RAG
    TEXT_EMBEDDING_MODEL_ID: str = "sentence-transformers/all-MiniLM-L6-v2"
    RERANKING_CROSS_ENCODER_MODEL_ID: str = "cross-encoder/ms-marco-MiniLM-L-4-v2"
    RAG_MODEL_DEVICE: str = "cpu"

    # Comet ML

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

    def export(self) -> None:
        """
        Exports the settings to the ZenML secret store.
        """

        env_vars = settings.model_dump()
        for key, value in env_vars.items():
            env_vars[key] = str(value)

        client = Client()

        try:
            client.create_secret(name="settings", values=env_vars)
        except EntityExistsError:
            logger.warning(
                "Secret 'scope' already exists. Delete it manually by running 'zenml secret delete settings', before trying to recreate it."
            )


settings = Settings.load_settings()
