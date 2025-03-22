from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


def process_user_input(user_input: str) -> dict:
    candidate_labels = [
        "check email",
        "list emails",
        "read emails",
        "create calendar event",
        "list calendar events",
        "create task",
        "list tasks",
        "web search",
        "update transactions",
        "unknown",
    ]
    result = classifier(user_input, candidate_labels)
    return {
        "intent": result["labels"][0],
        "confidence": result["scores"][0],
        "original_text": user_input,
    }
