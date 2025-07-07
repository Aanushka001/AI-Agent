from google.oauth2 import service_account
from googleapiclient.discovery import build
from backend.config import GOOGLE_CREDENTIALS_FILE, GOOGLE_CALENDAR_ID

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)

def create_event(start_time: str, end_time: str, summary: str, timeZone="UTC", location=None, conference=False):
    service = get_calendar_service()
    try:
        calendars = service.calendarList().list().execute()
        for cal in calendars.get('items', []):
            print(f"  - {cal.get('id')}: {cal.get('summary')}")
    except Exception as e:
        print(f"[DEBUG] Error listing calendars: {e}")
    print(f"[DEBUG] Using calendar ID: {GOOGLE_CALENDAR_ID}")
    event = {
        'summary': summary,
        'start': {'dateTime': start_time, 'timeZone': timeZone},
        'end': {'dateTime': end_time, 'timeZone': timeZone},
    }
    if location:
        event['location'] = location
    if conference:
        event['conferenceData'] = {
            'createRequest': {
                'requestId': f"meet-{start_time.replace(':','').replace('-','')}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    response = service.events().insert(
        calendarId=GOOGLE_CALENDAR_ID,
        body=event,
        conferenceDataVersion=1 if conference else 0
    ).execute()
    print("[DEBUG] Event creation response:", response)
    return response

def check_availability(start_time: str, end_time: str):
    service = get_calendar_service()
    body = {
        "timeMin": start_time,
        "timeMax": end_time,
        "timeZone": "UTC",
        "items": [{"id": GOOGLE_CALENDAR_ID}],
    }
    events_result = service.freebusy().query(body=body).execute()
    busy_times = events_result["calendars"][GOOGLE_CALENDAR_ID]["busy"]
    return busy_times
