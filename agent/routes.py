# agent/routes.py
import logging
from fastapi import APIRouter, Body
from ai.nlp_engine import process_user_input
from ai.decision import decide_next_action
from db.user_preferences import set_user_preference

router = APIRouter()

@router.post("/process")
def process_command(user_input: str = Body(...)):
    # 1. NLP
    parsed_output = process_user_input(user_input)
    logging.info(f"User input: {user_input} | Intent: {parsed_output['intent']} | Confidence: {parsed_output['confidence']}")
    # 2. Decision calls the registry
    decision = decide_next_action(parsed_output)
    # 3. Return the result from the tool
    return {"parsed": parsed_output, "decision": decision}

@router.post("/user_preferences")
def update_preference(user_id: str, pref_key: str, pref_value: float):
    set_user_preference(user_id, pref_key, pref_value)
    return {"message": "Preference updated!"}