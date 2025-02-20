# ai/decision.py
from typing import Dict, Any
from tools.tool_registry import find_tool_for_intent
from db.user_preferences import get_user_preference

def decide_next_action(parsed_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    1. Finds a tool that can handle the recognized intent.
    2. Tells that tool to parse_and_execute().
    3. If no tool found, fallback to a "can't handle" message.
    """
    intent = parsed_input.get("intent", "unknown")
    confidence = parsed_input.get("confidence", 0.0)
    user_text = parsed_input.get("original_text", "")
    user_confidence_threshold = get_user_preference("louis", "min_confidence_threshold")

    # For simplicity, let's do a simple confidence check
    if confidence < user_confidence_threshold:
        return {
            "tool": "none",
            "action": "not_sure",
            "message": f"Low confidence ({confidence:.2f}). Please rephrase."
        }

    tool = find_tool_for_intent(intent)
    if not tool:
        return {
            "tool": "none",
            "action": "no_tool_available",
            "message": f"No tool handles intent '{intent}'."
        }

    # We pass 'intent' to the tool as well, so it knows which flow to use
    tool_response = tool.parse_and_execute(user_text, intent=intent)
    return tool_response
