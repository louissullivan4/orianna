import os
import pickle
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

import pytz
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from tools.base_tool import BaseTool

SCOPES = ["https://www.googleapis.com/auth/calendar"]
API_NAME = "calendar"
API_VERSION = "v3"
TOKEN_FILE = "google_calendar_token.pickle"
CREDS_FILE_NAME = "google_credentials.json"


class CreateCalendarEventInput(BaseModel):
    summary: str
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class GetCalendarEventInput(BaseModel):
    context: str = Field(..., description="Time context: e.g., 'today', 'tomorrow', 'next week'")
    max_results: Optional[int] = Field(5, description="Maximum number of events to retrieve.")


class GoogleCalendarTool(BaseTool):
    def __init__(self) -> None:
        super().__init__()
        base_dir = os.path.dirname(__file__)
        self.token_path = os.path.join(base_dir, "pickles", TOKEN_FILE)
        self.creds_path = os.path.join(base_dir, "config", CREDS_FILE_NAME)

    def get_name(self) -> str:
        return "calendar_tool"

    def can_handle_intent(self, intent: str) -> bool:
        return intent in ["create calendar event", "list calendar events"]

    def get_system_prompt(self) -> str:
        return (
            "You are a parameter-extraction assistant for creating calendar events.\n"
            "Output ONLY JSON with fields:\n"
            '{ "summary": "<string>", "start_time": "<ISO8601 datetime>",'
            ' "end_time": "<ISO8601 datetime or empty>",'
            ' "location": "<string or empty>",'
            ' "description": "<string or empty>" }\n'
            "No extra text."
        )

    def parse_and_execute(self, user_text: str, **kwargs) -> Dict[str, Any]:
        intent = kwargs.get("intent", "")
        if intent == "create calendar event":
            return self._create_event_flow(user_text)
        elif intent == "list calendar events":
            # Extract context from user_text
            context = self._extract_context(user_text)
            input_params = GetCalendarEventInput(context=context)
            events = self._fetch_events_by_context(input_params)
            return {
                "tool": self.get_name(),
                "action": "list_events",
                "result": events,
                "summary": self._get_event_summaries(events),
                "message": f"Found {len(events)} upcoming events based on context '{input_params.context}'.",
            }
        else:
            return {
                "tool": self.get_name(),
                "action": "unknown_intent",
                "message": f"CalendarTool cannot handle '{intent}'.",
            }

    def _extract_context(self, text: str) -> str:
        lower_text = text.lower()
        if "next week" in lower_text:
            return "next week"
        elif "tomorrow" in lower_text:
            return "tomorrow"
        elif "today" in lower_text:
            return "today"
        else:
            # Default to next 7 days if no clear context is found.
            return "next 7 days"

    def _create_event_flow(self, user_text: str) -> Dict[str, Any]:
        tool_args = self._extract_params_via_llm(user_text)
        if "error" in tool_args:
            return {
                "tool": self.get_name(),
                "action": "create_event",
                "message": f"LLM extraction error: {tool_args['error']}",
            }
        try:
            event_input = CreateCalendarEventInput(**tool_args)
        except Exception as e:
            return {
                "tool": self.get_name(),
                "action": "create_event",
                "message": f"Invalid parameters: {str(e)}",
            }
        new_event = self._insert_event(event_input)
        return {
            "tool": self.get_name(),
            "action": "create_event",
            "result": new_event,
            "message": f"Event '{event_input.summary}' created.",
            "summary": f"Event '{event_input.summary}' created.",
        }

    def _fetch_events_by_context(self, input_params: GetCalendarEventInput) -> List[Dict[str, Any]]:
        service = self._get_calendar_service()
        dublin_tz = pytz.timezone("Europe/Dublin")
        now_local = datetime.now(dublin_tz)
        
        if input_params.context.lower() == "today":
            start_local = datetime.combine(now_local.date(), time.min).replace(tzinfo=dublin_tz)
            end_local = datetime.combine(now_local.date(), time.max).replace(tzinfo=dublin_tz)
        elif input_params.context.lower() == "tomorrow":
            tomorrow = now_local.date() + timedelta(days=1)
            start_local = datetime.combine(tomorrow, time.min).replace(tzinfo=dublin_tz)
            end_local = datetime.combine(tomorrow, time.max).replace(tzinfo=dublin_tz)
        elif input_params.context.lower() == "next week":
            # Calculate next Monday (start of next week)
            days_ahead = 7 - now_local.weekday()  # weekday(): Monday=0 ... Sunday=6
            if days_ahead == 0:
                days_ahead = 7
            next_monday = now_local.date() + timedelta(days=days_ahead)
            # End on next Sunday
            next_sunday = next_monday + timedelta(days=6)
            start_local = datetime.combine(next_monday, time.min).replace(tzinfo=dublin_tz)
            end_local = datetime.combine(next_sunday, time.max).replace(tzinfo=dublin_tz)
        else:
            # Default: next 7 days from now
            start_local = now_local
            end_local = now_local + timedelta(days=7)

        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)
        time_min = self._to_utc_rfc3339(start_utc)
        time_max = self._to_utc_rfc3339(end_utc)

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                singleEvents=True,
                orderBy="startTime",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=input_params.max_results,
            )
            .execute()
        )
        return events_result.get("items", [])

    def _insert_event(self, event_input: CreateCalendarEventInput) -> Dict[str, Any]:
        service = self._get_calendar_service()
        dublin_tz = pytz.timezone("Europe/Dublin")
        now_in_dublin = datetime.now(dublin_tz)
        start_dt_local = self._parse_date(event_input.start_time, now_in_dublin)
        end_dt_local = self._parse_date(event_input.end_time, start_dt_local) if event_input.end_time else start_dt_local + timedelta(hours=1)
        start_dt_utc = start_dt_local.astimezone(timezone.utc)
        end_dt_utc = end_dt_local.astimezone(timezone.utc)

        event_body = {
            "summary": event_input.summary,
            "start": {"dateTime": (start_dt_utc).isoformat()},
            "end": {"dateTime": (end_dt_utc).isoformat()},
        }
        if event_input.location:
            event_body["location"] = event_input.location
        if event_input.description:
            event_body["description"] = event_input.description

        return service.events().insert(calendarId="primary", body=event_body).execute()

    def _parse_date(self, date_str: str, relative_base: datetime) -> datetime:
        import dateparser
        parsed_dt = dateparser.parse(
            date_str,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": relative_base,
                "TIMEZONE": "Europe/Dublin",
                "TO_TIMEZONE": "Europe/Dublin",
            }
        )
        if not parsed_dt:
            parsed_dt = relative_base
        if parsed_dt < relative_base:
            parsed_dt += timedelta(days=7)
        return parsed_dt

    def _get_event_summaries(self, events: list) -> str:
        summary_str = f"Found {len(events)} upcoming events. "
        for event in events:
            print(event)
            event_summary = event.get("summary", "No summary")
            start_info = event.get("start", {})
            start_dt = self._convert_to_readable(start_info)
            event_location = event.get("location", "")
            if event_location:
                summary_str += f"{event_summary} at {start_dt} in {event_location}, "
            else:
                summary_str += f"{event_summary} at {start_dt}, "
        return summary_str

    def _convert_to_readable(self, start_info: dict) -> str:
        if start_info:
            iso_str = start_info.get("dateTime")
            tz_name = start_info.get("timeZone", "UTC")
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            dt = dt.astimezone(ZoneInfo(tz_name))
            return dt.strftime("%A, %B %d, %Y at %I:%M %p")
        return ""

    def _get_calendar_service(self):
        creds = self._load_credentials()
        if not creds or not creds.valid:
            creds = self._refresh_or_authorize_credentials(creds)
            self._save_credentials(creds)
        return build(API_NAME, API_VERSION, credentials=creds)

    def _load_credentials(self):
        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                return pickle.load(token)
        return None

    def _refresh_or_authorize_credentials(self, creds):
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        return creds

    def _save_credentials(self, creds):
        with open(self.token_path, "wb") as token:
            pickle.dump(creds, token)

    def _to_utc_rfc3339(self, dt: datetime) -> str:
        dt_utc = dt.astimezone(timezone.utc).replace(microsecond=0)
        return dt_utc.isoformat().replace("+00:00", "Z")
