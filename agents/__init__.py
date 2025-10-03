# agents/__init__.py - Task Agent System
"""
Complete Task Agent System for Academic AI Assistant
Handles calendar, email, file, and web automation
"""

from .calendar_manager import CalendarManager
from .email_manager import EmailManager
from .file_manager import FileManager
from .web_app_manager import WebAppManager

# Initialize global instances
calendar_manager = CalendarManager()
email_manager = EmailManager()
file_manager = FileManager()
web_app_manager = WebAppManager()

__all__ = [
    'calendar_manager',
    'email_manager', 
    'file_manager',
    'web_app_manager',
    'CalendarManager',
    'EmailManager',
    'FileManager',
    'WebAppManager'
]