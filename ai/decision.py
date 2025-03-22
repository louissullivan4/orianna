from typing import Dict, Any
from tools.tool_registry import find_tool_for_intent
from db.user_preferences import get_user_preference

def decide_next_action(parsed: Dict[str, Any]) -> Dict[str, Any]:
    intent = parsed.get("intent", "unknown")
    confidence = parsed.get("confidence", 0.0)
    user_text = parsed.get("original_text", "")
    threshold = get_user_preference("louis", "min_confidence_threshold")
    print(f"Intent: {intent}, confidence: {confidence}, threshold: {threshold}")
    if confidence < threshold:
        # return {"tool": "none", "action": "not_sure", "message": f"Low confidence ({confidence:.2f}). Please rephrase."}
        intent = "unknown"
    tool = find_tool_for_intent(intent)
    if not tool:
        return {"tool": "none", "action": "no_tool_available", "message": f"No tool handles intent '{intent}'."}
    return tool.parse_and_execute(user_text, intent=intent)
