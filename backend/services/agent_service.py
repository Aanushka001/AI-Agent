import os
from datetime import datetime, timedelta
from typing import TypedDict, Dict, Any, Literal
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import SecretStr
from backend.services.google_calendar_service import create_event, check_availability as gcal_check_availability

"""
Required environment variables (set in .env or system):
- OPENROUTER_API_KEY: Your OpenRouter API key
- GOOGLE_CLIENT_ID: Google Calendar OAuth client ID
- GOOGLE_CLIENT_SECRET: Google Calendar OAuth client secret
- GOOGLE_REFRESH_TOKEN: Google Calendar OAuth refresh token
"""

load_dotenv()

# Load OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable not set")

# Load Google Calendar credentials
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")

if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN):
    raise ValueError("Google Calendar credentials (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN) must be set in environment or .env file.")

class AgentState(TypedDict):
    input: str
    output: str
    tool_name: Literal["book_meeting", "check_availability"] | None
    tool_args: Dict[str, Any] | None
    tool_result: str | None
    history: list | None

@tool
def book_meeting(start_time: str, end_time: str, summary: str, timeZone="UTC", location=None, conference=False) -> str:
    """Book a meeting in Google Calendar."""
    try:
        event = create_event(start_time, end_time, summary, timeZone=timeZone, location=location, conference=conference)
        print("Event creation response:", event)
        html_link = event.get('htmlLink')
        msg = f"Booked: {summary} from {start_time} to {end_time} (Event ID: {event.get('id', 'N/A')})"
        if html_link:
            msg += f"\n[View in Google Calendar]({html_link})"
        return msg
    except Exception as e:
        return f"Error booking meeting: {str(e)}"

@tool
def check_availability(date: str, duration_minutes: int = 30) -> str:
    """Check calendar availability."""
    try:
        start_time = datetime.fromisoformat(date).isoformat()
        end_time = (datetime.fromisoformat(date) + timedelta(minutes=duration_minutes)).isoformat()
        busy_slots = gcal_check_availability(start_time, end_time)
        if busy_slots:
            return f"Busy during: {busy_slots}"
        else:
            return f"Available from {start_time} to {end_time}"
    except Exception as e:
        return f"Error checking availability: {str(e)}"

def create_agent():
    api_key: str = OPENROUTER_API_KEY  # type: ignore
    
    llm = ChatOpenAI(
        model="qwen/qwen3-32b",
        base_url="https://openrouter.ai/api/v1",
        api_key=SecretStr(api_key),
        default_headers={
            "HTTP-Referer": "https://your-frontend-url.com",
            "X-Title": "Calendar Agent"
        }
    )

    workflow = StateGraph(AgentState)

    def llm_node(state: AgentState):
        # Health check: if input is 'ping', return immediately
        if state["input"].strip().lower() == "ping":
            return {"output": "pong"}
        messages = []
        # Add a system prompt to make the agent conversational and calendar-focused
        system_prompt = (
            "You are a helpful, friendly AI assistant that helps users book and manage appointments on their Google Calendar. "
            "Always reply in a conversational, natural way, confirming actions and asking for clarification if needed. "
            "If a booking or availability result is present, summarize it in a friendly way before showing the details."
        )
        messages.append({"role": "system", "content": system_prompt})
        # Add chat history if present
        history = state.get("history")
        if history:
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(ToolMessage(content=msg["content"], tool_call_id="tool_call_1"))
        # Add the new user input
        if state["input"]:
            messages.append(HumanMessage(content=state["input"]))
        tool_result = state.get("tool_result")
        if tool_result is not None:
            messages.append(ToolMessage(content=str(tool_result), tool_call_id="tool_call_1"))
        response = llm.invoke(messages)
        # Friendly summary for tool results
        tool_result = state.get("tool_result")
        if isinstance(tool_result, str) and tool_result:
            friendly_prefix = "Here's what I did for you: " if "Booked:" in tool_result else "Here's what I found: "
            return {"output": f"{response.content}\n\n{friendly_prefix}{tool_result}"}
        else:
            return {"output": response.content}

    def tool_node(state: AgentState):
        if not state["tool_name"]:
            return state
        args = state["tool_args"] or {}
        if state["tool_name"] == "book_meeting":
            # Only pass supported args
            filtered_args = {k: v for k, v in args.items() if k in ["start_time", "end_time", "summary", "timeZone", "location", "conference"]}
            result = book_meeting.invoke(filtered_args)
        elif state["tool_name"] == "check_availability":
            result = check_availability.invoke(args)
        else:
            return state
        return {"tool_result": result}

    def route_to_tools(state: AgentState):
        output = state["output"].lower()
        # Book meeting extraction
        if "book" in output:
            # Try to extract start_time, end_time, summary from output
            import re
            import dateutil.parser
            # Example: "Book a meeting with John at 1 AM tomorrow."
            summary_match = re.search(r"book (?:a )?meeting(?: with ([\w\s]+))?", output)
            summary = summary_match.group(1).strip() if summary_match and summary_match.group(1) else "Meeting"
            # Find time (very basic, for demo)
            time_match = re.search(r"at ([\d:apm\s]+)", output)
            if time_match:
                time_str = time_match.group(1).strip()
                try:
                    from datetime import datetime, timedelta
                    import pytz
                    now = datetime.now()
                    # Try to parse time (assume tomorrow if 'tomorrow' in output)
                    if "tomorrow" in output:
                        date = now + timedelta(days=1)
                    else:
                        date = now
                    # Parse time
                    parsed_time = dateutil.parser.parse(time_str, default=date)
                    # If parsed_time is in the past, move to next day
                    now_check = datetime.now()
                    if parsed_time < now_check:
                        parsed_time = now_check + timedelta(days=1)
                    start_time = parsed_time.isoformat()
                    end_time = (parsed_time + timedelta(minutes=30)).isoformat()
                except Exception:
                    start_time = end_time = None
            else:
                start_time = end_time = None
            if start_time and end_time and summary:
                return {"tool_name": "book_meeting", "tool_args": {"start_time": start_time, "end_time": end_time, "summary": summary}}
            else:
                return {"output": state["output"]}
        elif "check" in output or "available" in output:
            # Try to extract date and duration
            import re
            date_match = re.search(r"on ([\w\s\-]+)", output)
            duration_match = re.search(r"for (\d+) minutes", output)
            date = date_match.group(1).strip() if date_match else None
            duration = int(duration_match.group(1)) if duration_match else 30
            if date:
                return {"tool_name": "check_availability", "tool_args": {"date": date, "duration_minutes": duration}}
            else:
                return {"output": state["output"]}
        return {"output": state["output"]}

    workflow.add_node("llm", llm_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("route", route_to_tools)

    workflow.set_entry_point("llm")
    workflow.add_edge("tools", "llm")
    workflow.add_conditional_edges(
        "llm",
        lambda state: bool(route_to_tools(state).get("tool_name")),
        {True: "route", False: END}
    )
    workflow.add_edge("route", "tools")

    return workflow.compile()

agent = create_agent()