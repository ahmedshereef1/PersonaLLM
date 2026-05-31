from loguru import logger
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from services.settings import settings


class MongoDatabaseConnection:
    _instance: MongoClient | None = None

    def __new__(cls, *args, **kwargs) -> MongoClient:
        if cls._instance is None:
            try:
                cls._instance = MongoClient(settings.DATABASE_HOST)
            except ConnectionFailure as e:
                logger.info(f"Faield to connect to the database: {e!s}")
                raise
        logger.info(
            f"Connection to MongoDB with URI successful: {settings.DATABASE_HOST}"
        )

        return cls._instance


connection = MongoDatabaseConnection()
