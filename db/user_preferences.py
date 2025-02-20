from .mongo_client import get_database

def get_user_preference(user_id: str, pref_key: str):
    """
    Retrieves a specific preference for a given user from MongoDB.
    """
    db = get_database()
    prefs_col = db["user_preferences"]
    
    doc = prefs_col.find_one({"user_id": user_id})
    if doc and pref_key in doc:
        return doc[pref_key]
    return None

def set_user_preference(user_id: str, pref_key: str, pref_value):
    """
    Sets/updates a user preference in MongoDB.
    """
    db = get_database()
    prefs_col = db["user_preferences"]
    
    prefs_col.update_one(
        {"user_id": user_id},
        {"$set": {pref_key: pref_value}},
        upsert=True
    )
