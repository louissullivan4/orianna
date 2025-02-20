# Orianna Assistant

Orianna is designed to be your all-in-one personal assistant that simplifies your day-to-day tasks. It uses natural language processing to understand your spoken or written commands and automatically selects the right tool—whether it's for managing your Gmail, scheduling events on your calendar, or organizing your tasks and other incoming tools.... i.e. Make my life easier

## How the Flow Works
User → /process: A user POSTs a text command, e.g. "Create a new task called 'Buy milk'...".
NLP Classification (nlp_engine.py): The system detects intent (e.g., "create task") and confidence score.
Decision (decision.py): Checks if confidence is high enough and finds the relevant tool (tasks_tool or gmail_tool, etc.) via tool_registry.
Tool Execution: The chosen tool’s parse_and_execute(user_input) is called.
Parameter Extraction: Tools can do naive regex or LLM-based extraction (via BaseTool._extract_params_via_llm).
Pydantic Validation: The tool checks the returned parameters.
Google API Call: The tool (e.g., GoogleTasksTool) calls the actual API.
Result: Returns a JSON dict with success or error info.
Response: /process returns {"parsed": {...}, "decision": {...}} describing the tool’s result.

## Run
uvicorn agent.main:app --port 8012
