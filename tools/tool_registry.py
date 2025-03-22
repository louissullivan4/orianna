from typing import List
from tools.base_tool import BaseTool
from tools.google_calendar_tool import GoogleCalendarTool
from tools.google_tasks_tool import GoogleTasksTool
from tools.gmail_tool import GmailTool
from tools.web_search_tool import WebSearchTool
from tools.revolut_tool import RevolutTool

def get_all_tools() -> List[BaseTool]:
    return [
            GoogleCalendarTool(), 
            GoogleTasksTool(), 
            GmailTool(), 
            # RevolutTool(),
            WebSearchTool()
        ]

def find_tool_for_intent(intent: str) -> BaseTool:
    for tool in get_all_tools():
        if tool.can_handle_intent(intent):
            return tool
    return None
