import os
import pickle
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tools.base_tool import BaseTool

class CreateTaskInput(BaseModel):
    title: str = Field(..., description="Title of the task")
    notes: Optional[str] = None
    due: Optional[str] = Field(None, description="Due date/time in RFC3339")

class GoogleTasksTool(BaseTool):
    SCOPES = ["https://www.googleapis.com/auth/tasks"]
    API_NAME = "tasks"
    API_VERSION = "v1"
    TOKEN_PATH = os.path.join(os.path.dirname(__file__), "pickles", "google_tasks_token.pickle")
    CREDS_FILE = os.path.join(os.path.dirname(__file__), "config", "google_credentials.json")

    def get_name(self) -> str:
        return "tasks_tool"

    def can_handle_intent(self, intent: str) -> bool:
        return intent in ["create task", "list tasks"]

    def parse_and_execute(self, user_text: str, **kwargs) -> Dict[str, Any]:
        intent = kwargs.get("intent", "")
        if intent == "create task":
            return self._create_task_flow(user_text)
        if intent == "list tasks":
            return self._list_tasks_flow()
        return {"tool": self.get_name(), "action": "unknown_intent", "message": f"TasksTool cannot handle '{intent}'."}

    def get_system_prompt(self) -> str:
        return (
            "You are a parameter-extraction assistant for creating tasks.\n"
            "Output ONLY JSON with fields:\n"
            '{ "title": "<string>", "notes": "<string or empty>", "due": "<RFC3339 date or empty>" }\n'
            "No extra text."
        )

    def _create_task_flow(self, user_text: str) -> Dict[str, Any]:
        tool_args = self._extract_params_via_llm(user_text)
        if "error" in tool_args:
            return {"tool": self.get_name(), "action": "create_task", "message": f"LLM extraction error: {tool_args['error']}"}
        try:
            task_input = CreateTaskInput(**tool_args)
        except Exception as e:
            return {"tool": self.get_name(), "action": "create_task", "message": f"Invalid parameters: {str(e)}"}
        new_task = self._create_task_in_gtasks(task_input)
        return {"tool": self.get_name(), "action": "create_task", "result": new_task, "message": f"Task '{task_input.title}' created."}

    def _list_tasks_flow(self) -> Dict[str, Any]:
        tasks = self._list_tasks()
        return {"tool": self.get_name(), "action": "list_tasks", "result": tasks, "message": f"Found {len(tasks)} tasks."}

    def _create_task_in_gtasks(self, task_input: CreateTaskInput):
        service = self._get_tasks_service()
        body = {"title": task_input.title}
        if task_input.notes:
            body["notes"] = task_input.notes
        if task_input.due:
            body["due"] = task_input.due
        return service.tasks().insert(tasklist="@default", body=body).execute()

    def _list_tasks(self):
        service = self._get_tasks_service()
        response = service.tasks().list(tasklist="@default").execute()
        return response.get("items", [])

    def _get_tasks_service(self):
        creds = None
        if os.path.exists(self.TOKEN_PATH):
            with open(self.TOKEN_PATH, "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.CREDS_FILE, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.TOKEN_PATH, "wb") as token:
                pickle.dump(creds, token)
        return build(self.API_NAME, self.API_VERSION, credentials=creds)
