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
    pending_event: Dict[str, Any] | None  # Store last proposed event

@tool
def book_meeting(start_time: str, end_time: str, summary: str, timeZone="UTC", location=None, conference=False) -> str:
    """Book a meeting in Google Calendar."""
    try:
        event = create_event(start_time, end_time, summary, timeZone=timeZone, location=location, conference=conference)
        html_link = event.get('htmlLink')
        from datetime import datetime
        import pytz
        dt = datetime.fromisoformat(start_time)
        local_dt = dt.astimezone(pytz.timezone(timeZone))
        date_str = local_dt.strftime('%B %d, %Y')
        time_str = local_dt.strftime('%I:%M %p')
        msg = f"Booked: {summary} on {date_str} at {time_str} ({timeZone}) for 30 minutes."
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

def extract_timezone(text: str):
    import pytz
    import re
    # List of words to ignore (common English words)
    ignore_words = set([
        "the", "my", "your", "another", "local", "what", "which", "a", "an", "at", "in", "on", "for", "to", "by"
    ])
    # 1. Handle 'local time' or 'my time'
    if re.search(r'\b(local|my) time\b', text, re.IGNORECASE):
        return "Asia/Kolkata"  # or your preferred default
    # 2. Check for common abbreviations
    tz_abbrs = set(['IST', 'UTC', 'PST', 'EST', 'CST', 'MST', 'EDT', 'PDT', 'BST', 'CET', 'EET', 'JST', 'AEST', 'AEDT', 'GMT'])
    abbr_map = {
        'IST': 'Asia/Kolkata',
        'PST': 'US/Pacific',
        'EST': 'US/Eastern',
        'CST': 'US/Central',
        'MST': 'US/Mountain',
        'EDT': 'US/Eastern',
        'PDT': 'US/Pacific',
        'BST': 'Europe/London',
        'CET': 'Europe/Paris',
        'EET': 'Europe/Athens',
        'JST': 'Asia/Tokyo',
        'AEST': 'Australia/Sydney',
        'AEDT': 'Australia/Sydney',
        'GMT': 'Etc/GMT',
        'UTC': 'UTC'
    }
    for abbr in tz_abbrs:
        if re.search(rf'\\b{abbr}\\b', text, re.IGNORECASE):
            return abbr_map.get(abbr.upper(), abbr.upper())
    # 3. Check for full timezone names in the text
    for zone in pytz.all_timezones:
        if zone.replace('_', ' ').lower() in text.lower():
            return zone
    # 4. If a word before 'time' or 'timezone' is in ignore_words, skip it
    match = re.search(r"(\b\w+\b) (?:time|timezone)", text.lower())
    if match:
        candidate = match.group(1).strip()
        if candidate not in ignore_words and candidate in pytz.all_timezones:
            return candidate
    # 5. Fallback
    return "Asia/Kolkata"

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
            filtered_args = {k: v for k, v in args.items() if k in ["start_time", "end_time", "summary", "timeZone", "location", "conference"]}
            result = book_meeting.invoke(filtered_args)
            return {"tool_result": result, "pending_event": None}
        elif state["tool_name"] == "check_availability":
            result = check_availability.invoke(args)
            return {"tool_result": result}
        else:
            return state

    def route_to_tools(state: AgentState):
        import dateparser
        import pytz
        import re
        output = state["output"].lower()
        # Confirmation logic
        if "confirm" in output or "book it" in output or "yes, book" in output:
            pending = state.get("pending_event")
            if pending:
                return {"tool_name": "book_meeting", "tool_args": pending, "pending_event": None}
            else:
                return {"output": "There is no pending event to confirm. Please specify the meeting details."}
        # Book meeting extraction
        if "book" in output:
            summary_match = re.search(r"book (?:a )?meeting(?: with ([\w\s]+))?", output)
            summary = summary_match.group(1).strip() if summary_match and summary_match.group(1) else "Meeting"
            time_match = re.search(r"at ([^.,;\n]+)", output)
            time_str = time_match.group(1).strip() if time_match else None
            timezone = extract_timezone(output)
            if timezone not in pytz.all_timezones:
                timezone = "Asia/Kolkata"
            now = datetime.now(pytz.timezone(timezone))
            if time_str:
                parsed_time = dateparser.parse(
                    time_str,
                    settings={
                        "TIMEZONE": timezone,
                        "RETURN_AS_TIMEZONE_AWARE": True,
                        "PREFER_DATES_FROM": "future",
                        "RELATIVE_BASE": now
                    }
                )
            else:
                parsed_time = None
            if parsed_time and "tomorrow" in output:
                parsed_time = parsed_time + timedelta(days=1)
            if not parsed_time or parsed_time < now:
                return {"output": "Sorry, I couldn't understand the meeting time or it was in the past. Please specify a future date and time (e.g., 'Book a meeting tomorrow at 3pm IST')."}
            start_time = parsed_time.isoformat()
            end_time = (parsed_time + timedelta(minutes=30)).isoformat()
            # Store pending event for confirmation
            pending_event = {"start_time": start_time, "end_time": end_time, "summary": summary, "timeZone": timezone}
            confirm_msg = f"I'll check your availability for the 1 PM - 1:30 PM slot on {parsed_time.strftime('%B %d, %Y')}. Is that correct? (Time zone will default to {timezone} unless specified.)\nLet me know if you'd like to adjust or confirm the booking!"
            return {"output": confirm_msg, "pending_event": pending_event}
        elif "check" in output or "available" in output:
            import dateparser
            import pytz
            import re
            # Try to extract date/time phrase
            date_match = re.search(r"on ([^.,;\n]+)", output)
            time_match = re.search(r"at ([^.,;\n]+)", output)
            duration_match = re.search(r"for (\d+) minutes", output)
            duration = int(duration_match.group(1)) if duration_match else 30
            timezone = extract_timezone(output)
            if timezone not in pytz.all_timezones:
                timezone = "Asia/Kolkata"
            now = datetime.now(pytz.timezone(timezone))
            # Build a phrase to parse
            phrase = ""
            if date_match:
                phrase += date_match.group(1).strip() + " "
            if time_match:
                phrase += time_match.group(1).strip()
            phrase = phrase.strip()
            parsed_time = dateparser.parse(
                phrase,
                settings={
                    "TIMEZONE": timezone,
                    "RETURN_AS_TIMEZONE_AWARE": True,
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": now
                }
            )
            if not parsed_time or parsed_time < now:
                return {"output": "Sorry, I couldn't understand the date/time for availability. Please specify a future date and time (e.g., 'Check availability on July 10th at 3pm IST')."}
            start_time = parsed_time.isoformat()
            end_time = (parsed_time + timedelta(minutes=duration)).isoformat()
            return {"tool_name": "check_availability", "tool_args": {"start_time": start_time, "end_time": end_time}}
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