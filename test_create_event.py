import os
print("GOOGLE_CREDENTIALS_FILE (env):", os.getenv("GOOGLE_CREDENTIALS_FILE"))
print("GOOGLE_CALENDAR_ID (env):", os.getenv("GOOGLE_CALENDAR_ID"))
import backend.config
print("Loaded config file:", backend.config.GOOGLE_CREDENTIALS_FILE)
print("Loaded calendar ID:", backend.config.GOOGLE_CALENDAR_ID)
from backend.services.google_calendar_service import create_event

# Example values (adjust as needed)
start_time = "2025-07-14T11:30:00+05:30"  # ISO 8601 format, with timezone offset
end_time = "2025-07-14T12:30:00+05:30"
summary = "Direct API Test Event"
timeZone = "Asia/Kolkata"
location = "Conference Room"
conference = True

event = create_event(
    start_time=start_time,
    end_time=end_time,
    summary=summary,
    timeZone=timeZone,
    location=location,
    conference=False
)

print("Event creation response:")
print(event)
print("Google Calendar link:", event.get("htmlLink"))