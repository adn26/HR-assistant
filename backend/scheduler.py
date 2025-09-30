import os
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# loading env location explicitly cause some error with loading env variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """
    Authenticate and return Google Calendar service
    
    Setup instructions:
    1. Enable Google Calendar API in Google Cloud Console
    2. Download OAuth credentials (Desktop App) JSON
    3. Either name it 'credentials.json' in this directory or set env GOOGLE_CREDENTIALS_PATH
       Optionally set GOOGLE_TOKEN_PATH to customize token storage location
    """
    creds = None
    
    # token file stores user's access and refresh tokens
    token_path = os.getenv('GOOGLE_TOKEN_PATH', os.path.join(os.path.dirname(__file__), 'token.pickle'))
    creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', os.path.join(os.path.dirname(__file__), 'credentials.json'))
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # if no valid credentials let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"Google OAuth credentials not found at '{creds_path}'. Set GOOGLE_CREDENTIALS_PATH or place 'credentials.json' next to scheduler.py."
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            try:
                # Preferred: opens a browser and captures the callback automatically
                creds = flow.run_local_server(port=0)
            except Exception:
                # Fallback for headless/remote environments: copy-paste code in terminal
                creds = flow.run_console()
        
        # save credentials for next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    service = build('calendar', 'v3', credentials=creds)
    return service

# schedules interviews for selected candidates on Google Calendar
async def schedule_interviews(
    candidates: List[Dict],
    start_date: datetime,
    duration_minutes: int = 60,gap_minutes: int = 15,
    calendar_id: str = 'primary'
) -> List[Dict]:
    
    try:
        service = get_calendar_service()
    except Exception as e:
        print(f"Calendar authentication error: {e}")
        # return mock data for testing without calendar access
        return create_mock_schedule(candidates, start_date, duration_minutes)
    
    scheduled_interviews = []
    current_time = start_date
    
    for candidate in candidates:
        interview_start = current_time
        interview_end = current_time + timedelta(minutes=duration_minutes)
        
        event = {
            'summary': f'Interview: {candidate.get("name", "Candidate")}',
            'description': f"""
            Interview with {candidate.get("name", "Candidate")}
            Position: As per job description
            Candidate Email: {candidate.get("email", "N/A")}
            Candidate Phone: {candidate.get("phone", "N/A")}

            Skills: {', '.join(candidate.get("skills", []))}
            Experience: {candidate.get("experience_years", "N/A")} years

            Match Score: {candidate.get("score", "N/A")}/100
            """.strip(),
            'start': {
                'dateTime': interview_start.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': interview_end.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': candidate.get('email', '')},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        try:
            created_event = service.events().insert(
                calendarId=calendar_id,
                body=event,
                sendUpdates='all'  # Send email notifications
            ).execute()
            
            scheduled_interviews.append({
                'candidate_name': candidate.get('name', 'Unknown'),
                'candidate_email': candidate.get('email', ''),
                'interview_start': interview_start.isoformat(),
                'interview_end': interview_end.isoformat(),
                'calendar_event_id': created_event['id'],
                'calendar_link': created_event.get('htmlLink', ''),
                'status': 'scheduled'
            })
            
            print(f"✓ Scheduled interview for {candidate.get('name')} at {interview_start}")
            
        except Exception as e:
            print(f"✗ Failed to schedule interview for {candidate.get('name')}: {e}")
            scheduled_interviews.append({
                'candidate_name': candidate.get('name', 'Unknown'),
                'candidate_email': candidate.get('email', ''),
                'interview_start': interview_start.isoformat(),
                'interview_end': interview_end.isoformat(),
                'status': 'failed',
                'error': str(e)
            })
        
        # move to next slot
        current_time = interview_end + timedelta(minutes=gap_minutes)
    
    return scheduled_interviews

# create mock schedule data for testing without calendar access
def create_mock_schedule(candidates: List[Dict], start_date: datetime, duration_minutes: int) -> List[Dict]:
    scheduled_interviews = []
    current_time = start_date
    
    for candidate in candidates:
        interview_start = current_time
        interview_end = current_time + timedelta(minutes=duration_minutes)
        
        scheduled_interviews.append({
            'candidate_name': candidate.get('name', 'Unknown'),
            'candidate_email': candidate.get('email', ''),
            'interview_start': interview_start.isoformat(),
            'interview_end': interview_end.isoformat(),
            'calendar_event_id': f'mock_event_{candidate.get("name", "unknown")}',
            'calendar_link': 'https://calendar.google.com/calendar/',
            'status': 'scheduled_mock'
        })
        
        current_time = interview_end + timedelta(minutes=15)
    
    return scheduled_interviews

if __name__ == "__main__":
    # test
    import asyncio
    
    async def test():
        test_candidates = [
            {
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "phone": "+1234567890",
                "skills": ["Python", "React"],
                "score": 95
            },
            {
                "name": "Bob Smith",
                "email": "bob@example.com",
                "phone": "+0987654321",
                "skills": ["JavaScript", "Node.js"],
                "score": 88
            }
        ]
        
        start = datetime.now() + timedelta(days=2)
        scheduled = await schedule_interviews(test_candidates, start)
        
        for interview in scheduled:
            print(f"{interview['candidate_name']}: {interview['interview_start']}")
    
    asyncio.run(test())