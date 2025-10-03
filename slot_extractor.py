# slot_extractor.py - Enhanced slot extraction with better parsing
import dateparser
import datetime
import re
from typing import Tuple, Optional, List

def extract_datetime(command: str) -> Tuple[Optional[datetime.datetime], float]:
    """
    Extract datetime and optional duration from natural text.
    Returns (datetime_obj, duration_hours)
    """
    command = command.lower().strip()
    duration_hours = 1  # default

    # Duration extraction
    duration_match = re.search(r"for (\d+)\s*(hour|hours|hr|hrs|minute|minutes|min|mins)", command)
    if duration_match:
        value = int(duration_match.group(1))
        unit = duration_match.group(2).lower()
        if "min" in unit:
            duration_hours = value / 60
        else:
            duration_hours = value

    # Handle 'next <weekday>' manually
    match = re.search(r"\bnext (\w+day)\b", command)
    if match:
        weekday_str = match.group(1).lower()
        weekdays = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
        if weekday_str in weekdays:
            today = datetime.datetime.now()
            today_weekday = today.weekday()
            target_weekday = weekdays.index(weekday_str)
            days_ahead = (target_weekday - today_weekday + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_date = today + datetime.timedelta(days=days_ahead)

            # Look for a time part
            time_match = re.search(r"(\d{1,2}(:\d{2})?\s*(am|pm)?)", command)
            if time_match:
                time_str = time_match.group(1)
                dt = dateparser.parse(f"{next_date.strftime('%Y-%m-%d')} {time_str}")
                return dt, duration_hours
            return next_date.replace(hour=9, minute=0), duration_hours

    # Fallback to dateparser
    dt = dateparser.parse(command, settings={"PREFER_DATES_FROM": "future"})
    return dt, duration_hours if dt else (None, None)

def extract_subject_body(command: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract subject and body from email/calendar commands.
    Returns (subject, body)
    """
    # Remove common command words
    cleaned = re.sub(r'\b(send|email|schedule|meeting|about|saying|tell|inform)\b', '', command, flags=re.IGNORECASE)
    
    # Extract subject from patterns like "about X" or "regarding Y"
    subject_patterns = [
        r'about\s+([^,\.]+)',
        r'regarding\s+([^,\.]+)',
        r'for\s+([^,\.]+)',
        r'subject:?\s*([^,\.]+)',
        r'"([^"]+)"',  # Quoted text
        r'\'([^\']+)\''  # Single quoted text
    ]
    
    subject = None
    for pattern in subject_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            subject = match.group(1).strip().title()
            break
    
    # Extract body from patterns like "saying X" or "message: Y"
    body_patterns = [
        r'saying\s+([^,\.]+)',
        r'message:?\s*([^,\.]+)',
        r'body:?\s*([^,\.]+)',
        r'tell\s+them\s+([^,\.]+)',
        r'inform\s+them\s+([^,\.]+)'
    ]
    
    body = None
    for pattern in body_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            body = match.group(1).strip()
            break
    
    # If no specific subject found, try to extract from the remaining text
    if not subject:
        # Remove recipients and common words
        potential_subject = re.sub(r'\b(to|send|email)\b', '', cleaned, flags=re.IGNORECASE).strip()
        if len(potential_subject) > 5:
            subject = potential_subject[:50].title()  # Limit length
    
    return subject, body

def extract_recipient(command: str) -> List[str]:
    """
    Extract recipient information from commands.
    Returns list of recipient identifiers (names, groups, etc.)
    """
    recipients = []
    
    # Extract names after "to"
    to_pattern = r'\bto\s+([^,\.]+)'
    to_match = re.search(to_pattern, command, re.IGNORECASE)
    if to_match:
        recipient_text = to_match.group(1).strip()
        # Split by "and" or ","
        parts = re.split(r'\s+and\s+|,\s*', recipient_text)
        recipients.extend([part.strip() for part in parts if part.strip()])
    
    # Extract group indicators
    group_patterns = [
        r'\ball\s+students?\b',
        r'\ball\s+staff\b',
        r'\bfaculty\b',
        r'\bteam\b',
        r'\bgroup\b'
    ]
    
    for pattern in group_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            recipients.append(re.search(pattern, command, re.IGNORECASE).group(0))
    
    return recipients

def extract_location(command: str) -> Optional[str]:
    """Extract location/venue information from commands."""
    location_patterns = [
        r'\bat\s+([^,\.]+(?:room|hall|center|office|building)[^,\.]*)',
        r'\bin\s+([^,\.]+(?:room|hall|center|office|building)[^,\.]*)',
        r'\bvenue:?\s*([^,\.]+)',
        r'\blocation:?\s*([^,\.]+)',
        r'\bplace:?\s*([^,\.]+)'
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    
    return None

def extract_priority(command: str) -> str:
    """Extract priority level from commands."""
    if re.search(r'\b(urgent|asap|immediately|critical|high priority)\b', command, re.IGNORECASE):
        return "high"
    elif re.search(r'\b(low priority|when possible|no rush)\b', command, re.IGNORECASE):
        return "low"
    else:
        return "normal"

def extract_contact_info(command: str) -> dict:
    """Extract various contact information from commands."""
    contact_info = {}
    
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, command)
    if emails:
        contact_info['emails'] = emails
    
    # Phone numbers (basic patterns)
    phone_patterns = [
        r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
        r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',  # (123) 456-7890
        r'\b\d{10}\b'  # 1234567890
    ]
    
    phones = []
    for pattern in phone_patterns:
        phones.extend(re.findall(pattern, command))
    
    if phones:
        contact_info['phones'] = phones
    
    return contact_info

def extract_file_info(command: str) -> dict:
    """Extract file-related information from commands."""
    file_info = {}
    
    # File extensions
    file_pattern = r'\b[\w-]+\.(?:pdf|doc|docx|txt|csv|xlsx|ppt|pptx|jpg|png|zip)\b'
    files = re.findall(file_pattern, command, re.IGNORECASE)
    if files:
        file_info['files'] = files
    
    # Folder/directory references
    folder_patterns = [
        r'\bfolder\s+([^\s,\.]+)',
        r'\bdirectory\s+([^\s,\.]+)',
        r'\bpath\s+([^\s,\.]+)'
    ]
    
    folders = []
    for pattern in folder_patterns:
        matches = re.findall(pattern, command, re.IGNORECASE)
        folders.extend(matches)
    
    if folders:
        file_info['folders'] = folders
    
    return file_info

def extract_time_constraints(command: str) -> dict:
    """Extract time-related constraints and preferences."""
    constraints = {}
    
    # Deadline patterns
    deadline_patterns = [
        r'\bby\s+([^,\.]+)',
        r'\bdeadline:?\s*([^,\.]+)',
        r'\bbefore\s+([^,\.]+)',
        r'\bdue\s+([^,\.]+)'
    ]
    
    for pattern in deadline_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            deadline_text = match.group(1).strip()
            deadline_dt = dateparser.parse(deadline_text)
            if deadline_dt:
                constraints['deadline'] = deadline_dt
                break
    
    # Recurring patterns
    recurring_patterns = [
        r'\b(daily|every day)\b',
        r'\b(weekly|every week)\b',
        r'\b(monthly|every month)\b',
        r'\bevery\s+(\w+day)\b'
    ]
    
    for pattern in recurring_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            constraints['recurring'] = match.group(0).lower()
            break
    
    return constraints

def extract_numbers_and_quantities(command: str) -> dict:
    """Extract numeric information from commands."""
    numbers = {}
    
    # Duration in different units
    duration_patterns = [
        (r'(\d+)\s*hours?', 'hours'),
        (r'(\d+)\s*minutes?', 'minutes'),
        (r'(\d+)\s*days?', 'days'),
        (r'(\d+)\s*weeks?', 'weeks')
    ]
    
    for pattern, unit in duration_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            numbers[f'duration_{unit}'] = int(match.group(1))
    
    # Count/quantity
    count_patterns = [
        r'(\d+)\s*people',
        r'(\d+)\s*attendees',
        r'(\d+)\s*participants',
        r'(\d+)\s*copies',
        r'(\d+)\s*files'
    ]
    
    for pattern in count_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            numbers['count'] = int(match.group(1))
            break
    
    return numbers

def extract_all_slots(command: str) -> dict:
    """Extract all possible slots from a command."""
    slots = {}
    
    # Basic extractions
    dt, duration = extract_datetime(command)
    if dt:
        slots['datetime'] = dt
        slots['duration'] = duration
    
    subject, body = extract_subject_body(command)
    if subject:
        slots['subject'] = subject
    if body:
        slots['body'] = body
    
    recipients = extract_recipient(command)
    if recipients:
        slots['recipients'] = recipients
    
    location = extract_location(command)
    if location:
        slots['location'] = location
    
    # Advanced extractions
    slots['priority'] = extract_priority(command)
    
    contact_info = extract_contact_info(command)
    if contact_info:
        slots['contact_info'] = contact_info
    
    file_info = extract_file_info(command)
    if file_info:
        slots['file_info'] = file_info
    
    time_constraints = extract_time_constraints(command)
    if time_constraints:
        slots['time_constraints'] = time_constraints
    
    numbers = extract_numbers_and_quantities(command)
    if numbers:
        slots['numbers'] = numbers
    
    return slots

def validate_slots(slots: dict) -> dict:
    """Validate extracted slots and add confidence scores."""
    validated = {}
    
    for key, value in slots.items():
        confidence = 1.0
        
        if key == 'datetime' and value:
            # Check if datetime is reasonable (not too far in past/future)
            now = datetime.datetime.now()
            if value < now - datetime.timedelta(days=1):
                confidence = 0.3  # Likely past date
            elif value > now + datetime.timedelta(days=365):
                confidence = 0.5  # Very far future
            
        elif key == 'subject' and value:
            # Check subject length and content
            if len(value) < 3:
                confidence = 0.4
            elif len(value) > 100:
                confidence = 0.6
                
        elif key == 'recipients' and value:
            # Check if recipients look valid
            for recipient in value:
                if len(recipient) < 2:
                    confidence = min(confidence, 0.5)
        
        validated[key] = {
            'value': value,
            'confidence': confidence
        }
    
    return validated