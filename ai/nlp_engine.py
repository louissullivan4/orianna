# ai/nlp_engine.py
from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def process_user_input(user_input: str) -> dict:
    candidate_labels = [
        "check email",
        "list calendar",
        "create calendar event",
        "list tasks",
        "create task",
        "unknown"
    ]
    result = classifier(user_input, candidate_labels)
    top_label = result["labels"][0]
    score = result["scores"][0]

    return {
        "intent": top_label,
        "confidence": score,
        "original_text": user_input
    }
