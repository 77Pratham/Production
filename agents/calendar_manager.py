# agents/calendar_manager.py - Google Calendar Integration
"""
Calendar Manager Agent for Academic AI Assistant
Handles Google Calendar events, reminders, and scheduling
"""

import os
import pickle
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class CalendarManager:
    """Manages Google Calendar operations with fallback to local calendar"""
    
    def __init__(self):
        self.calendar_service = None
        self.use_google_calendar = False
        self.local_events = []  # Fallback local storage
        
        # Try to initialize Google Calendar
        self._initialize_google_calendar()
    
    def _initialize_google_calendar(self):
        """Initialize Google Calendar API"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            creds = None
            
            # Load saved credentials
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            
            # Get new credentials if needed
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif os.path.exists('client_secrets_file.json'):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'client_secrets_file.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    logger.info("Google Calendar credentials not found. Using local calendar.")
                    return
                
                # Save credentials
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            
            # Build calendar service
            self.calendar_service = build('calendar', 'v3', credentials=creds)
            self.use_google_calendar = True
            logger.info("✅ Google Calendar initialized successfully")
            
        except ImportError:
            logger.info("Google Calendar libraries not installed. Using local calendar.")
        except Exception as e:
            logger.warning(f"Google Calendar initialization failed: {e}. Using local calendar.")
    
    def create_event(self, summary: str, start_time: str, duration: float = 1.0, 
                    description: str = "", location: str = "", 
                    attendees: List[str] = None) -> str:
        """
        Create calendar event
        
        Args:
            summary: Event title
            start_time: Start time in format "YYYY-MM-DD HH:MM"
            duration: Duration in hours
            description: Event description
            location: Event location
            attendees: List of attendee emails
        
        Returns:
            Success message with event details
        """
        try:
            # Parse start time
            start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(hours=duration)
            
            event_data = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': start_dt,
                'end': end_dt,
                'attendees': attendees or []
            }
            
            if self.use_google_calendar and self.calendar_service:
                return self._create_google_event(event_data)
            else:
                return self._create_local_event(event_data)
                
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return f"❌ Error creating event: {str(e)}"
    
    def _create_google_event(self, event_data: Dict) -> str:
        """Create event in Google Calendar"""
        try:
            event = {
                'summary': event_data['summary'],
                'location': event_data['location'],
                'description': event_data['description'],
                'start': {
                    'dateTime': event_data['start'].isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': event_data['end'].isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'attendees': [{'email': email} for email in event_data['attendees']],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},  # 30 min before
                    ],
                },
            }
            
            created_event = self.calendar_service.events().insert(
                calendarId='primary', 
                body=event,
                sendUpdates='all'  # Send invitations to attendees
            ).execute()
            
            event_link = created_event.get('htmlLink')
            
            return f"""✅ Google Calendar event created successfully!

📌 Event: {event_data['summary']}
🕐 Time: {event_data['start'].strftime('%d %B %Y, %I:%M %p')}
⏱️  Duration: {(event_data['end'] - event_data['start']).seconds / 3600:.1f} hours
📍 Location: {event_data['location'] or 'Not specified'}
👥 Attendees: {len(event_data['attendees'])} invited
🔗 Link: {event_link}

📧 Email invitations sent to all attendees!"""
            
        except Exception as e:
            logger.error(f"Google Calendar error: {e}")
            return self._create_local_event(event_data)
    
    def _create_local_event(self, event_data: Dict) -> str:
        """Create event in local storage (fallback)"""
        event_data['id'] = len(self.local_events) + 1
        event_data['created_at'] = datetime.now()
        self.local_events.append(event_data)
        
        # Save to file
        self._save_local_events()
        
        return f"""✅ Calendar event created (local storage)!

📌 Event: {event_data['summary']}
🕐 Time: {event_data['start'].strftime('%d %B %Y, %I:%M %p')}
⏱️  Duration: {(event_data['end'] - event_data['start']).seconds / 3600:.1f} hours
📍 Location: {event_data['location'] or 'Not specified'}
👥 Attendees: {len(event_data['attendees'])}

💡 Note: Install Google Calendar API for cloud sync"""
    
    def list_upcoming_events(self, max_results: int = 10) -> List[str]:
        """List upcoming calendar events"""
        
        if self.use_google_calendar and self.calendar_service:
            return self._list_google_events(max_results)
        else:
            return self._list_local_events(max_results)
    
    def _list_google_events(self, max_results: int) -> List[str]:
        """List events from Google Calendar"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return ["📅 No upcoming events found."]
            
            event_list = ["📅 Upcoming Events:\n"]
            for i, event in enumerate(events, 1):
                start = event['start'].get('dateTime', event['start'].get('date'))
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                
                event_list.append(
                    f"{i}. {event['summary']}\n"
                    f"   📅 {start_dt.strftime('%d %B %Y, %I:%M %p')}\n"
                    f"   📍 {event.get('location', 'No location')}\n"
                )
            
            return event_list
            
        except Exception as e:
            logger.error(f"Error listing Google events: {e}")
            return self._list_local_events(max_results)
    
    def _list_local_events(self, max_results: int) -> List[str]:
        """List events from local storage"""
        
        if not self.local_events:
            return ["📅 No upcoming events found. (Local storage)"]
        
        # Filter future events
        now = datetime.now()
        upcoming = [e for e in self.local_events if e['start'] > now]
        upcoming.sort(key=lambda x: x['start'])
        
        if not upcoming:
            return ["📅 No upcoming events found."]
        
        event_list = ["📅 Upcoming Events (Local):\n"]
        for i, event in enumerate(upcoming[:max_results], 1):
            event_list.append(
                f"{i}. {event['summary']}\n"
                f"   📅 {event['start'].strftime('%d %B %Y, %I:%M %p')}\n"
                f"   📍 {event.get('location', 'No location')}\n"
            )
        
        return event_list
    
    def delete_event(self, event_id: str) -> str:
        """Delete calendar event"""
        
        if self.use_google_calendar and self.calendar_service:
            try:
                self.calendar_service.events().delete(
                    calendarId='primary',
                    eventId=event_id
                ).execute()
                return "✅ Event deleted successfully from Google Calendar"
            except Exception as e:
                logger.error(f"Error deleting event: {e}")
                return f"❌ Error deleting event: {str(e)}"
        else:
            # Delete from local storage
            try:
                event_id_int = int(event_id)
                self.local_events = [e for e in self.local_events if e['id'] != event_id_int]
                self._save_local_events()
                return "✅ Event deleted from local calendar"
            except:
                return "❌ Event not found"
    
    def update_event(self, event_id: str, updates: Dict) -> str:
        """Update calendar event"""
        
        if self.use_google_calendar and self.calendar_service:
            try:
                event = self.calendar_service.events().get(
                    calendarId='primary',
                    eventId=event_id
                ).execute()
                
                # Update fields
                for key, value in updates.items():
                    event[key] = value
                
                updated_event = self.calendar_service.events().update(
                    calendarId='primary',
                    eventId=event_id,
                    body=event
                ).execute()
                
                return f"✅ Event updated: {updated_event.get('summary')}"
                
            except Exception as e:
                logger.error(f"Error updating event: {e}")
                return f"❌ Error updating event: {str(e)}"
        else:
            return "❌ Event update not available in local mode"
    
    def _save_local_events(self):
        """Save local events to file"""
        try:
            with open('local_calendar_events.pickle', 'wb') as f:
                pickle.dump(self.local_events, f)
        except Exception as e:
            logger.error(f"Error saving local events: {e}")
    
    def _load_local_events(self):
        """Load local events from file"""
        try:
            if os.path.exists('local_calendar_events.pickle'):
                with open('local_calendar_events.pickle', 'rb') as f:
                    self.local_events = pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading local events: {e}")
            self.local_events = []
    
    def get_free_slots(self, date: str, duration_hours: float = 1.0) -> List[str]:
        """Find free time slots on a given date"""
        
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            
            # Business hours: 9 AM to 5 PM
            start_time = target_date.replace(hour=9, minute=0)
            end_time = target_date.replace(hour=17, minute=0)
            
            # Get events for that day
            if self.use_google_calendar and self.calendar_service:
                events = self._get_events_for_date(target_date)
            else:
                events = [e for e in self.local_events 
                         if e['start'].date() == target_date.date()]
            
            # Find free slots
            free_slots = []
            current_time = start_time
            
            for event in sorted(events, key=lambda x: x['start']):
                if current_time < event['start']:
                    # Free slot found
                    slot_duration = (event['start'] - current_time).seconds / 3600
                    if slot_duration >= duration_hours:
                        free_slots.append(
                            f"{current_time.strftime('%I:%M %p')} - "
                            f"{event['start'].strftime('%I:%M %p')}"
                        )
                current_time = max(current_time, event['end'])
            
            # Check remaining time after last event
            if current_time < end_time:
                slot_duration = (end_time - current_time).seconds / 3600
                if slot_duration >= duration_hours:
                    free_slots.append(
                        f"{current_time.strftime('%I:%M %p')} - "
                        f"{end_time.strftime('%I:%M %p')}"
                    )
            
            if free_slots:
                return [f"📅 Free slots on {date}:"] + free_slots
            else:
                return [f"❌ No free slots available on {date}"]
                
        except Exception as e:
            logger.error(f"Error finding free slots: {e}")
            return [f"❌ Error: {str(e)}"]
    
    def _get_events_for_date(self, date: datetime) -> List[Dict]:
        """Get all events for a specific date from Google Calendar"""
        try:
            time_min = date.replace(hour=0, minute=0).isoformat() + 'Z'
            time_max = date.replace(hour=23, minute=59).isoformat() + 'Z'
            
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = []
            for event in events_result.get('items', []):
                start = event['start'].get('dateTime')
                end = event['end'].get('dateTime')
                if start and end:
                    events.append({
                        'summary': event['summary'],
                        'start': datetime.fromisoformat(start.replace('Z', '+00:00')),
                        'end': datetime.fromisoformat(end.replace('Z', '+00:00'))
                    })
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting events for date: {e}")
            return []