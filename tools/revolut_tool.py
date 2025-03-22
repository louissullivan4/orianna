import os
from typing import Any, Dict, List
from tools.base_tool import BaseTool
import pandas as pd
from transformers import pipeline
from tools.google_sheets_tool import GoogleSheetsTool

class RevolutTool(BaseTool):
    def get_name(self) -> str:
        return "revolut_tool"

    def can_handle_intent(self, intent: str) -> bool:
        return intent in ["update transactions"]

    def get_system_prompt(self) -> str:
        return (
            "None"
    #         "Output ONLY JSON with fields:\n"
    #         '{ "from_date": "<string in YYYY-MM-DD format>", "count": <integer> }\n'
    #         "If user doesn't mention from_date, default to 30 days back.\n"
    #         "If user doesn't mention count, default to 100."
        )

    def parse_and_execute(self, user_text: str, **kwargs) -> Dict[str, Any]:
        intent = kwargs.get("intent", "")
        if not self.can_handle_intent(intent):
            return {
                "tool": self.get_name(),
                "action": "unknown_intent",
                "message": f"RevolutTool cannot handle intent '{intent}'"
            }
        return self._update_transactions_flow()

    def _update_transactions_flow(self) -> Dict[str, Any]:
        transactions = self._get_transactions_from_xlsx()
        
        output_xlsx_path = os.path.join(os.path.dirname(__file__), "input_files", "new.xlsx")
        pd.DataFrame(transactions).to_excel(output_xlsx_path, index=False)
        pd.DataFrame(transactions).to_csv(os.path.join(os.path.dirname(__file__), "input_files", "new1.csv"), index=False)
        pd.DataFrame(transactions).to_string(os.path.join(os.path.dirname(__file__), "input_files", "new2.txt"), index=False)
        
        # gst = GoogleSheetsTool()
        
        return {"tool": self.get_name(), "action": "update_transactions", "message": f"Updated transactions in '{output_xlsx_path}'."}
    
    def _get_grouping(self, description: str, txn_type: str) -> str:
        classifier_model = pipeline("text-classification", model="kuro-08/bert-transaction-categorization")
        description = str(description)
        txn_type = str(txn_type)
        
        if description.upper().startswith("APPLE PAY TOP"):
            return "Salary"
        elif description.upper().startswith("TO EUR"):
            return "SKIP"
        elif txn_type.upper() == "TRANSFER":
            return "Friends & Family"
        
        result = classifier_model(description)
        return result[0]["label"]

    def _get_transactions_from_xlsx(self) -> List[Dict[str, Any]]:
        INPUT_SHEET = os.path.join(os.path.dirname(__file__), "input_files", "latest.xlsx")
        df = pd.read_excel(INPUT_SHEET)
        df.columns = df.columns.str.strip()

        df["Category"] = df.apply(lambda row: self._get_grouping(row["Description"], row["Type"]), axis=1)
