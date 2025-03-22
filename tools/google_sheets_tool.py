import os
import pickle
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
google_credentials = None
if credentials_json:
    try:
        google_credentials = json.loads(credentials_json)
    except json.JSONDecodeError as e:
        raise ValueError("Invalid JSON in GOOGLE_CREDENTIALS_JSON") from e

class GoogleSheetsTool():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    API_NAME = "sheets"
    API_VERSION = "v4"
    TOKEN_PATH = os.path.join(os.path.dirname(__file__), "pickles", "google_sheets_token.pickle")
    CREDS_FILE = os.path.join(os.path.dirname(__file__), "config", "google_credentials.json")
    SPREADSHEET_ID = "13rWZUjJhB8Dw31kbedqN-B-Rc5fnVeV4"
    SHEET_NAME = "Worksheet"
    
    def get_name(self) -> str:
        return "GoogleSheetsTool"

    def parse_and_execute(self, output_xlsx_path: str) -> Dict[str, Any]:
        if not output_xlsx_path or not os.path.exists(output_xlsx_path):
            return {"tool": self.get_name(), "action": "update_spreadsheet", "message": f"Local file '{output_xlsx_path}' not found."}
        
        latest_online_date = self._get_latest_completed_date_online()
        if latest_online_date is None:
            latest_online_date = datetime.min
        else:
            latest_online_date = datetime.fromisoformat(latest_online_date)
        
        df_local = pd.read_excel(output_xlsx_path)
        df_local["Completed Date"] = pd.to_datetime(df_local["Completed Date"])
        new_rows = df_local[df_local["Completed Date"] > latest_online_date]
        
        if new_rows.empty:
            return {"tool": self.get_name(), "action": "update_spreadsheet", "message": "No new rows to update."}
        
        values = new_rows.values.tolist()
        update_result = self._append_rows_to_sheet(values)
        return {"tool": self.get_name(), "action": "update_spreadsheet", "result": update_result, "message": f"Appended {len(values)} new rows."}

    def _get_sheets_service(self):
        creds = None
        if os.path.exists(self.TOKEN_PATH):
            with open(self.TOKEN_PATH, "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if google_credentials:
                    flow = InstalledAppFlow.from_client_config(google_credentials, self.SCOPES)
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.CREDS_FILE, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.TOKEN_PATH, "wb") as token:
                pickle.dump(creds, token)
        return build(self.API_NAME, self.API_VERSION, credentials=creds)

    def _get_latest_completed_date_online(self) -> Optional[str]:
        service = self._get_sheets_service()
        range_name = f"{self.SHEET_NAME}!A:Z"
        result = service.spreadsheets().values().get(spreadsheetId=self.SPREADSHEET_ID, range=range_name).execute()
        rows = result.get("values", [])
        if not rows or len(rows) < 2:
            return None
        
        header = rows[0]
        try:
            col_index = header.index("Completed Date")
        except ValueError:
            return None
        
        completed_dates = []
        for row in rows[1:]:
            if len(row) > col_index and row[col_index]:
                try:
                    dt = datetime.fromisoformat(row[col_index])
                    completed_dates.append(dt)
                except Exception:
                    continue
        if completed_dates:
            latest_date = max(completed_dates)
            return latest_date.isoformat()
        return None

    def _append_rows_to_sheet(self, values: List[List[Any]]):
        service = self._get_sheets_service()
        range_name = f"{self.SHEET_NAME}!A1"
        body = {"values": values}
        result = service.spreadsheets().values().append(
            spreadsheetId=self.SPREADSHEET_ID,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        return result
