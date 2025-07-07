from fastapi import APIRouter, Request
from backend.services.google_calendar_service import create_event, check_availability
from backend.services.agent_service import create_agent, AgentState
from typing import cast

router = APIRouter()

@router.post("/book")
def book_event(start_time: str, end_time: str, summary: str):
    event = create_event(start_time, end_time, summary)
    return {"event_id": event.get("id"), "status": "success"}

@router.get("/availability")
def get_availability(start_time: str, end_time: str):
    busy_times = check_availability(start_time, end_time)
    return {"busy": busy_times}

@router.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message")
    agent = create_agent()
    response = agent.invoke(cast(AgentState, {
        "input": user_message,
        "output": "",
        "tool_name": None,
        "tool_args": None,
        "tool_result": None
    }))
    return {"response": response["output"]}
