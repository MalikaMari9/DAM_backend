from functools import lru_cache
from pymongo import MongoClient
from app.core.config import get_settings


@lru_cache(maxsize=1)
def _get_client() -> MongoClient:
    settings = get_settings()
    mongo_uri = getattr(settings, "mongo_uri", None)
    if not mongo_uri:
        raise RuntimeError("MONGO_URI is not set")
    return MongoClient(mongo_uri)


def get_imhe_collection():
    settings = get_settings()
    db_name = getattr(settings, "mongo_db_health", "Health")
    coll_name = getattr(settings, "mongo_collection_imhe", "IMHE")
    client = _get_client()
    return client[db_name][coll_name]


def get_openaq_collection():
    settings = get_settings()
    db_name = getattr(settings, "mongo_db_pollution", "Pollution")
    coll_name = getattr(settings, "mongo_collection_openaq", "OpenAQ")
    client = _get_client()
    return client[db_name][coll_name]
