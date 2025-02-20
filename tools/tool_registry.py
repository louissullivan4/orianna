# tools/tool_registry.py
from typing import List
from .base_tool import BaseTool

# Import your concrete tools
from .google_calendar_tool import GoogleCalendarTool
from .google_tasks_tool import GoogleTasksTool
from .gmail_tool import GmailTool  # example, if you want

def get_all_tools() -> List[BaseTool]:
    """
    Return a list of all tool instances.
    """
    return [
        GoogleCalendarTool(),
        GoogleTasksTool(),
        GmailTool()
        # add more as needed
    ]

def find_tool_for_intent(intent: str) -> BaseTool:
    """
    Find the first tool that can handle this intent.
    """
    for tool in get_all_tools():
        if tool.can_handle_intent(intent):
            return tool
    return None  # if no tool can handle
