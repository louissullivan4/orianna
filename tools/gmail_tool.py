# tools/gmail_tool.py

import os
import pickle
from typing import Dict, Any

from pydantic import BaseModel, Field
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .base_tool import BaseTool

class CheckGmailInboxInput(BaseModel):
    label_id: str = Field(default="INBOX")
    max_results: int = Field(default=5)

class GmailTool(BaseTool):
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def get_name(self) -> str:
        return "gmail_tool"

    def can_handle_intent(self, intent: str) -> bool:
        return intent in ["check email", "list emails", "read emails"]

    def parse_and_execute(self, user_text: str, **kwargs) -> Dict[str, Any]:
        intent = kwargs.get("intent", "")
        if not self.can_handle_intent(intent):
            return {
                "tool": self.get_name(),
                "action": "unknown_intent",
                "message": f"GmailTool cannot handle intent '{intent}'"
            }

        return self._check_inbox_flow(user_text)

    def get_system_prompt(self) -> str:
        """
        Tells the LLM how to produce JSON for checking Gmail:
        { "label_id":"...", "max_results":... }
        """
        return """You are a parameter-extraction assistant for checking Gmail.
Output ONLY JSON with fields:
{
  "label_id": "<string (INBOX, SPAM, etc.)>",
  "max_results": <integer>
}
No extra text.
If user doesn't mention max, default to 5.
If user doesn't mention label, default to "INBOX".
"""

    def _check_inbox_flow(self, user_text: str) -> Dict[str, Any]:
        # 1) LLM extraction
        tool_args = self._extract_params_via_llm(user_text)

        if "error" in tool_args:
            return {
                "tool": self.get_name(),
                "action": "check_inbox",
                "message": f"LLM extraction error: {tool_args['error']}"
            }

        # 2) Validate with Pydantic
        try:
            inbox_input = CheckGmailInboxInput(**tool_args)
        except Exception as e:
            return {
                "tool": self.get_name(),
                "action": "check_inbox",
                "message": f"Invalid parameters: {str(e)}"
            }

        # 3) Actually do the Gmail API call
        emails = self._check_gmail_inbox(label_id=inbox_input.label_id, max_results=inbox_input.max_results)
        return {
            "tool": self.get_name(),
            "action": "check_inbox",
            "result": emails,
            "message": f"Fetched {len(emails)} emails from label '{inbox_input.label_id}'."
        }

    def _check_gmail_inbox(self, label_id="INBOX", max_results=5):
        service = self._get_gmail_service()
        result = service.users().messages().list(
            userId='me', labelIds=[label_id], maxResults=max_results
        ).execute()

        messages = result.get('messages', [])
        emails = []
        for msg in messages or []:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            snippet = msg_data.get('snippet', '')
            headers = msg_data.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), None)
            sender = next((h['value'] for h in headers if h['name'] == 'From'), None)
            emails.append({
                "subject": subject,
                "from": sender,
                "snippet": snippet
            })
        return emails

    def _get_gmail_service(self):
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), 'pickles/google_gmail_token.pickle')
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
        
        service = build('gmail', 'v1', credentials=creds)
        return service
