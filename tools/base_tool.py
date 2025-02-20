# tools/base_tool.py

from abc import ABC, abstractmethod
from typing import Any, Dict
import json
import subprocess
from datetime import datetime, timezone

class BaseTool(ABC):
    """
    Base class that centralizes the local LLM extraction logic.
    Each tool can override get_system_prompt() to define 
    how the LLM should output fields for that tool.
    """

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def can_handle_intent(self, intent: str) -> bool:
        pass

    @abstractmethod
    def parse_and_execute(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """
        Each tool still implements this to handle Pydantic validation 
        and the final "action" logic. But it can call the shared 
        '_extract_params_via_llm' method below.
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Returns the system prompt instructions for the LLM, 
        telling it how to structure the JSON output for this tool's parameters.
        Example: 
        {
          "title": "<string>", 
          "notes": "<string>", 
          ...
        }
        """
        pass

    def _extract_params_via_llm(self, user_text: str, model_name="dolphin3") -> Dict[str, Any]:
        """
        A protected helper to do the local LLM call with your system prompt,
        parse the JSON. If error, returns {"error": "..."}.
        We add 'today' in ISO8601 so the LLM can interpret relative times 
        (e.g., "tomorrow") more accurately.
        """
        system_prompt = self.get_system_prompt()

        # Get current date/time in a friendly or ISO format
        # e.g., "2025-03-10T12:34:56Z"
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # Append a line telling the LLM "Today is <some date/time>"
        final_prompt = (
            f"{system_prompt}\n"
            f"Today is {now}.\n"
            f"User text: {user_text}"
        )

        cmd = [
            "ollama",
            "run",
            model_name,
            final_prompt
        ]
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = process.communicate()
            if err:
                print("LLM error:", err)

            parsed = json.loads(out.strip())
            print("LLM output:", parsed)
            return parsed
        except Exception as e:
            return {"error": str(e)}