# tools/google_tasks_tool.py

import os
import pickle
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .base_tool import BaseTool

class CreateTaskInput(BaseModel):
    title: str = Field(..., description="Title of the task")
    notes: Optional[str] = None
    due: Optional[str] = Field(None, description="Due date/time in RFC3339")

class GoogleTasksTool(BaseTool):
    SCOPES = ["https://www.googleapis.com/auth/tasks"]

    def get_name(self) -> str:
        return "tasks_tool"

    def can_handle_intent(self, intent: str) -> bool:
        return intent in ["create task", "list tasks"]

    def parse_and_execute(self, user_text: str, **kwargs) -> Dict[str, Any]:
        intent = kwargs.get("intent", "")
        if intent == "create task":
            return self._create_task_flow(user_text)
        elif intent == "list tasks":
            return self._list_tasks_flow()
        else:
            return {
                "tool": self.get_name(),
                "action": "unknown_intent",
                "message": f"TasksTool cannot handle '{intent}'."
            }

    def get_system_prompt(self) -> str:
        """
        Instruct the LLM on how to return JSON for a new task:
        { "title":"...", "notes":"...", "due":"..." }
        """
        return """You are a parameter-extraction assistant for creating tasks.
Output ONLY JSON with fields:
{
  "title": "<string>",
  "notes": "<string or empty>",
  "due": "<RFC3339 date or empty>"
}
No extra text.
"""

    # ------------------------------------------------
    # Private flows
    # ------------------------------------------------
    def _create_task_flow(self, user_text: str) -> Dict[str, Any]:
        # 1) Extract LLM arguments
        tool_args = self._extract_params_via_llm(user_text)

        # 2) Check for LLM errors
        if "error" in tool_args:
            return {
                "tool": self.get_name(),
                "action": "create_task",
                "message": f"LLM extraction error: {tool_args['error']}"
            }

        # 3) Validate with Pydantic
        try:
            task_input = CreateTaskInput(**tool_args)
        except Exception as e:
            return {
                "tool": self.get_name(),
                "action": "create_task",
                "message": f"Invalid parameters: {str(e)}"
            }

        # 4) Create in Google Tasks
        new_task = self._create_task_in_gtasks(task_input)
        return {
            "tool": self.get_name(),
            "action": "create_task",
            "result": new_task,
            "message": f"Task '{task_input.title}' created."
        }

    def _list_tasks_flow(self) -> Dict[str, Any]:
        tasks = self._list_tasks()
        return {
            "tool": self.get_name(),
            "action": "list_tasks",
            "result": tasks,
            "message": f"Found {len(tasks)} tasks."
        }

    # ------------------------------------------------
    # Google Tasks integration
    # ------------------------------------------------
    def _create_task_in_gtasks(self, task_input: CreateTaskInput):
        service = self._get_tasks_service()
        body = {"title": task_input.title}
        if task_input.notes:
            body["notes"] = task_input.notes
        if task_input.due:
            body["due"] = task_input.due
        return service.tasks().insert(tasklist='@default', body=body).execute()

    def _list_tasks(self):
        service = self._get_tasks_service()
        response = service.tasks().list(tasklist='@default').execute()
        return response.get('items', [])

    def _get_tasks_service(self):
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), 'pickles/google_tasks_token.pickle')
        creds_file = os.path.join(os.path.dirname(__file__), 'config/google_credentials.json')

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        return build('tasks', 'v1', credentials=creds)
