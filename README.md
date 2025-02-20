# Orianna Assistant

This project integrates a local LLM (Mistral 7B) with memory storage via PostgreSQL (using pgvector), fetches emails via the Gmail API, and now features a LangChain agent with tool selection. A FastAPI server is provided for external API access.

## Structure

- **src/agent/main.py:** CLI interface for interacting with the assistant.
- **src/agent/langchain_agent.py:** LangChain-based agent that selects the right tool based on the query.
- **src/server.py:** FastAPI server exposing an API endpoint.
- **src/agent/database.py, memory.py, tools, models:** Various modules for LLM integration, memory storage, and email handling.

## Next Steps

- Fine-tuning the LLM on personal data.
- Adding speech recognition & TTS.
- Expanding tools (budget tracker, home automation, etc.)


uvicorn agent.main:app --port 8012
