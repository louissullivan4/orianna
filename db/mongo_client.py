import os
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URL", "mongodb://root:example@localhost:27017/")
DB_NAME = os.environ.get("MONGO_DB_NAME", "orianna_db")

def get_mongo_client():
    return MongoClient(MONGO_URI)

def get_database():
    client = get_mongo_client()
    return client[DB_NAME]
