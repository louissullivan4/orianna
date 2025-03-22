import os
import pickle
import re
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from tools.base_tool import BaseTool

BASE_DIR = os.path.dirname(__file__)
PICKLES_DIR = os.path.join(BASE_DIR, "pickles")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
GMAIL_TOKEN_FILE = "google_gmail_token.pickle"
GMAIL_CREDS_FILE = "google_credentials.json"
TOKEN_PATH = os.path.join(PICKLES_DIR, GMAIL_TOKEN_FILE)
CREDS_PATH = os.path.join(CONFIG_DIR, GMAIL_CREDS_FILE)


class CheckGmailInboxInput(BaseModel):
    label_id: str = Field(default="INBOX")
    max_results: int = Field(default=5)
    sender_filter: Optional[str] = Field(default=None)


class GmailTool(BaseTool):
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def get_name(self) -> str:
        return "gmail_tool"

    def can_handle_intent(self, intent: str) -> bool:
        return intent in ["check email", "list emails", "read emails"]

    def get_system_prompt(self) -> str:
        return (
            "You are a parameter-extraction assistant for checking Gmail.\n"
            "Output ONLY JSON with fields:\n"
            '{ "label_id": "<string (INBOX, SPAM, etc.)>", "max_results": <integer>, "sender_filter": "<optional string>" }\n'
            "No extra text.\n"
            "If user doesn't mention max, default to 5.\n"
            "If user doesn't mention label, default to 'INBOX'.\n"
            "If user mentions a sender, set sender_filter."
        )

    def parse_and_execute(self, user_text: str, **kwargs) -> Dict[str, Any]:
        intent = kwargs.get("intent", "")
        if not self.can_handle_intent(intent):
            return {
                "tool": self.get_name(),
                "action": "unknown_intent",
                "message": f"GmailTool cannot handle intent '{intent}'",
            }
        return self._check_inbox_flow(user_text)

    def _check_inbox_flow(self, user_text: str) -> Dict[str, Any]:
        tool_args = self._extract_params_via_llm(user_text)
        if "error" in tool_args:
            return {
                "tool": self.get_name(),
                "action": "check_inbox",
                "message": f"LLM extraction error: {tool_args['error']}",
            }
        try:
            inbox_input = CheckGmailInboxInput(**tool_args)
        except Exception as e:
            return {
                "tool": self.get_name(),
                "action": "check_inbox",
                "message": f"Invalid parameters: {str(e)}",
            }

        emails = self._fetch_emails(
            label_id=inbox_input.label_id,
            max_results=inbox_input.max_results,
            sender_filter=inbox_input.sender_filter,
        )

        summary = "Emails: " + ", ".join(
            f"{self._extract_email(email['from'])} with subject '{self._normalize_text(email['subject'])}'"
            for email in emails
        )

        return {
            "tool": self.get_name(),
            "action": "check_inbox",
            "result": emails,
            "summary": summary,
            "message": f"Fetched {len(emails)} emails from label '{inbox_input.label_id}'.",
        }

    def _fetch_emails(
        self, label_id="INBOX", max_results=5, sender_filter=None
    ) -> List[Dict[str, Any]]:
        label_map = self._get_label_map()
        mapped_label_id = label_map.get(label_id.lower(), label_id)

        service = self._get_gmail_service()
        result = (
            service.users()
            .messages()
            .list(userId="me", labelIds=[mapped_label_id], maxResults=max_results)
            .execute()
        )

        messages = result.get("messages", [])
        emails = []
        for msg in messages or []:
            msg_data = (
                service.users().messages().get(userId="me", id=msg["id"]).execute()
            )
            headers = msg_data.get("payload", {}).get("headers", [])
            subject = self._get_header_value(headers, "Subject")
            sender = self._get_header_value(headers, "From")
            snippet = msg_data.get("snippet", "")

            if sender_filter and sender_filter.lower() not in sender.lower():
                continue

            emails.append({"subject": subject, "from": sender, "snippet": snippet})
        return emails

    def _get_gmail_service(self):
        creds = self._load_credentials()
        if not creds or not creds.valid:
            creds = self._refresh_or_authorize_credentials(creds)
            self._save_credentials(creds)
        return build("gmail", "v1", credentials=creds)

    def _load_credentials(self):
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, "rb") as token:
                return pickle.load(token)
        return None

    def _refresh_or_authorize_credentials(self, creds):
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, self.SCOPES)
            creds = flow.run_local_server(port=0)
        return creds

    def _save_credentials(self, creds):
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    @staticmethod
    def _get_label_map() -> Dict[str, str]:
        return {
            "inbox": "INBOX",
            "spam": "SPAM",
            "sent": "SENT",
            "drafts": "DRAFT",
            "important": "IMPORTANT",
            "starred": "STARRED",
            "trash": "TRASH",
            "promotions": "CATEGORY_PROMOTIONS",
            "social": "CATEGORY_SOCIAL",
            "updates": "CATEGORY_UPDATES",
            "forums": "CATEGORY_FORUMS",
            "primary": "CATEGORY_PRIMARY",
        }

    @staticmethod
    def _get_header_value(headers: List[Dict[str, str]], name: str) -> str:
        return next(
            (h["value"] for h in headers if h["name"].lower() == name.lower()), ""
        )

    @staticmethod
    def _extract_email(text: str) -> str:
        match = re.search(r"[\w\.-]+@[\w\.-]+", text)
        return match.group(0) if match else text

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(
            r"[^\x00-\x7F]+", "", text.replace("\n", " ").replace("\r", " ")
        ).strip()
