import json
import requests
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from tools.base_tool import BaseTool

GOOGLE_SEARCH_API_KEY = "AIzaSyCMFKRAd6Oo6vjSZZcaV00bJyR28ykHpDM"
GOOGLE_SEARCH_ENGINE_ID = "d0df8efc206344b23"

class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query to look up on the internet.")

class WebSearchTool(BaseTool):

    def get_name(self) -> str:
        return "websearch_tool"

    def can_handle_intent(self, intent: str) -> bool:
        return intent in ["web search", "unknown"]

    def get_system_prompt(self) -> str:
        return (
            "You are a parameter-extraction assistant for web search.\n"
            "Output ONLY JSON with a single field:\n"
            '{ "query": "<string representing the search query>" }\n'
            "No extra text, markdown, or explanation."
        )

    def parse_and_execute(self, user_text: str, **kwargs) -> Dict[str, Any]:
        search_results = self._perform_google_search(user_text)
        if "error" in search_results:
            return {
                "tool": self.get_name(),
                "action": "web_search",
                "message": f"Search failed: {search_results['error']}",
            }
        summary_prompt = (
            "You are a summarization assistant. Given the search results, summarize the key information clearly and concisely.\n"
            "Output ONLY JSON:\n"
            '{ "summary": "<concise summary of the search results>" }\n'
            "No extra text, markdown, or explanation."
        )
        summary = self._summarize_via_llm(search_results, summary_prompt)
        return {
            "tool": self.get_name(),
            "action": "web_search",
            "summary": summary,
            "message": f"Web search completed and summarized for query: '{user_text}'.",
        }

    def _perform_google_search(self, query: str) -> List[Dict[str, Any]]:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_SEARCH_API_KEY,
            "cx": GOOGLE_SEARCH_ENGINE_ID,
            "q": query,
            "num": 1,
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "title": item["title"],
                    "link": item["link"],
                    "snippet": item.get("snippet", "No description available."),
                }
                for item in data.get("items", [])
            ]
        except Exception as e:
            return {"error": str(e)}
