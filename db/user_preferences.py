from db.mongo_client import get_database

def get_user_preference(user_id: str, pref_key: str):
    db = get_database()
    doc = db["user_preferences"].find_one({"user_id": user_id})
    return doc.get(pref_key) if doc and pref_key in doc else None

def set_user_preference(user_id: str, pref_key: str, pref_value):
    db = get_database()
    db["user_preferences"].update_one({"user_id": user_id}, {"$set": {pref_key: pref_value}}, upsert=True)
