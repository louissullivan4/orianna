import json
import subprocess
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def can_handle_intent(self, intent: str) -> bool:
        pass

    @abstractmethod
    def parse_and_execute(self, user_input: str, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def _summarize_via_llm(self, data: Any, summary_prompt: str, model_name="dolphin3") -> str:
        if not isinstance(data, str):
            input_str = json.dumps(data, ensure_ascii=False)
        else:
            input_str = data

        final_prompt = f"{summary_prompt}\n\nData: {input_str}"
        try:
            response = self._call_llm(final_prompt, model_name=model_name)
            return response.get("summary", "Summarization failed.")
        except Exception as e:
            return f"Summarization error: {str(e)}"
        
    def _extract_params_via_llm(self, user_text: str, model_name="dolphin3") -> Dict[str, Any]:
        system_prompt = self.get_system_prompt()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        final_prompt = (
            f"{system_prompt}\n"
            f"Today is {now}.\n"
            f"User text: {user_text}"
        )
        return self._call_llm(final_prompt, model_name=model_name)

    def _call_llm(self, final_prompt: str, model_name="dolphin3") -> Dict[str, Any]:
        cmd = ["ollama", "run", model_name, final_prompt]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding="utf-8")
            out, err = proc.communicate()
            if err:
                print("LLM error:", err)
            return json.loads(out.strip())
        except Exception as e:
            return {"error": str(e)}
