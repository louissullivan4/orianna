# tools/google_calendar_tool.py

import os
import pickle
import dateparser
from datetime import timedelta
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .base_tool import BaseTool

class CreateCalendarEventInput(BaseModel):
    summary: str
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None

class GoogleCalendarTool(BaseTool):
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def get_name(self) -> str:
        return "calendar_tool"

    def can_handle_intent(self, intent: str) -> bool:
        return intent in ["create calendar event", "list calendar"]

    def parse_and_execute(self, user_text: str, **kwargs) -> Dict[str, Any]:
        intent = kwargs.get("intent", "")
        if intent == "create calendar event":
            return self._create_event_flow(user_text)
        elif intent == "list calendar":
            return self._list_events_flow()
        else:
            return {
                "tool": self.get_name(),
                "action": "unknown_intent",
                "message": f"CalendarTool cannot handle '{intent}'."
            }

    def get_system_prompt(self) -> str:
        """
        Tells the LLM how to produce JSON for a calendar event.
        """
        return """You are a parameter-extraction assistant for creating calendar events.
Output ONLY JSON with fields:
{
  "summary": "<string>",
  "start_time": "<ISO8601 datetime>",
  "end_time": "<ISO8601 datetime or empty>",
  "location": "<string or empty>",
  "description": "<string or empty>"
}
No extra text.
"""

    def _create_event_flow(self, user_text: str) -> Dict[str, Any]:
        tool_args = self._extract_params_via_llm(user_text)

        if "error" in tool_args:
            return {
                "tool": self.get_name(),
                "action": "create_event",
                "message": f"LLM extraction error: {tool_args['error']}"
            }

        try:
            event_input = CreateCalendarEventInput(**tool_args)
        except Exception as e:
            return {
                "tool": self.get_name(),
                "action": "create_event",
                "message": f"Invalid parameters: {str(e)}"
            }

        if not event_input.end_time:
            parsed_start = dateparser.parse(event_input.start_time)
            if parsed_start:
                event_input.end_time = (parsed_start + timedelta(hours=1)).isoformat()
            else:
                return {
                    "tool": self.get_name(),
                    "action": "create_event",
                    "message": "Could not parse start_time for the event."
                }

        new_event = self._create_event_in_gcal(event_input)
        return {
            "tool": self.get_name(),
            "action": "create_event",
            "result": new_event,
            "message": f"Event '{event_input.summary}' created."
        }

    def _list_events_flow(self, max_results=5) -> Dict[str, Any]:
        events = self._list_upcoming_events(max_results)
        return {
            "tool": self.get_name(),
            "action": "list_events",
            "result": events,
            "message": f"Found {len(events)} upcoming events."
        }

    def _create_event_in_gcal(self, event_input: CreateCalendarEventInput):
        service = self._get_calendar_service()
        event_body = {
            "summary": event_input.summary,
            "start": {"dateTime": event_input.start_time},
            "end": {"dateTime": event_input.end_time},
        }
        if event_input.location:
            event_body["location"] = event_input.location
        if event_input.description:
            event_body["description"] = event_input.description

        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        return created_event

    def _list_upcoming_events(self, max_results=5):
        service = self._get_calendar_service()
        events_result = service.events().list(
            calendarId='primary',
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    def _get_calendar_service(self):
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), 'pickles/google_calendar_token.pickle')
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
        return build('calendar', 'v3', credentials=creds)
