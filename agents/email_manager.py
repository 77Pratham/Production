# agents/email_manager.py - Email Sending Agent
"""
Email Manager Agent for Academic AI Assistant
Handles SMTP email sending with encryption and attachments
"""

import smtplib
import ssl
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailManager:
    """Manages email sending operations with SMTP"""
    
    def __init__(self):
        self.smtp_servers = {
            'gmail': ('smtp.gmail.com', 587),
            'outlook': ('smtp-mail.outlook.com', 587),
            'yahoo': ('smtp.mail.yahoo.com', 587),
            'office365': ('smtp.office365.com', 587)
        }
        self.sent_emails_log = []
    
    def send_email(self, sender_email: str, password: str, recipients: List[str],
                  subject: str, body: str, attachments: List[str] = None,
                  cc: List[str] = None, bcc: List[str] = None,
                  html: bool = False) -> str:
        """
        Send email using SMTP
        
        Args:
            sender_email: Sender's email address
            password: App password (not regular password!)
            recipients: List of recipient email addresses
            subject: Email subject
            body: Email body
            attachments: List of file paths to attach
            cc: CC recipients
            bcc: BCC recipients
            html: Whether body is HTML
        
        Returns:
            Success/failure message
        """
        
        # Demo mode - just log and return success
        if os.getenv('DEMO_MODE', 'true').lower() == 'true':
            return self._demo_send_email(sender_email, recipients, subject, body)
        
        try:
            # Detect email provider
            provider = self._detect_provider(sender_email)
            smtp_server, smtp_port = self.smtp_servers.get(provider, ('smtp.gmail.com', 587))
            
            # Create message
            message = MIMEMultipart()
            message['From'] = sender_email
            message['To'] = ', '.join(recipients)
            message['Subject'] = subject
            message['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            if cc:
                message['Cc'] = ', '.join(cc)
            if bcc:
                message['Bcc'] = ', '.join(bcc)
            
            # Attach body
            if html:
                message.attach(MIMEText(body, 'html'))
            else:
                message.attach(MIMEText(body, 'plain'))
            
            # Attach files
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        self._attach_file(message, file_path)
            
            # Create secure connection
            context = ssl.create_default_context()
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(sender_email, password)
                
                all_recipients = recipients + (cc or []) + (bcc or [])
                server.sendmail(sender_email, all_recipients, message.as_string())
            
            # Log sent email
            self._log_sent_email(sender_email, recipients, subject)
            
            return f"""✅ Email sent successfully!

📧 To: {', '.join(recipients[:3])}{'...' if len(recipients) > 3 else ''}
📨 Total recipients: {len(recipients)}
📋 Subject: {subject}
🕐 Sent at: {datetime.now().strftime('%I:%M %p')}"""
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed")
            return """❌ Email authentication failed!

💡 TIP: For Gmail, you need an "App Password":
   1. Go to Google Account settings
   2. Enable 2-Factor Authentication
   3. Generate App Password
   4. Use that password instead of your regular one"""
            
        except Exception as e:
            logger.error(f"Email sending error: {e}")
            return f"❌ Error sending email: {str(e)}"
    
    def _demo_send_email(self, sender: str, recipients: List[str], 
                        subject: str, body: str) -> str:
        """Demo mode - simulate email sending"""
        
        # Log to file
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'from': sender,
            'to': recipients,
            'subject': subject,
            'body_preview': body[:100]
        }
        self.sent_emails_log.append(log_entry)
        
        # Save to file
        try:
            os.makedirs('data/exports/sent_emails', exist_ok=True)
            log_file = f"data/exports/sent_emails/email_log_{datetime.now().strftime('%Y%m%d')}.txt"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"TIMESTAMP: {log_entry['timestamp']}\n")
                f.write(f"FROM: {sender}\n")
                f.write(f"TO: {', '.join(recipients)}\n")
                f.write(f"SUBJECT: {subject}\n")
                f.write(f"BODY PREVIEW:\n{body[:200]}...\n")
        except Exception as e:
            logger.error(f"Error logging email: {e}")
        
        return f"""✅ EMAIL COMPOSED SUCCESSFULLY! (Demo Mode)

📧 From: {sender}
📨 To: {len(recipients)} recipient(s)
   {', '.join([r.split('@')[0] for r in recipients[:3]])}{'...' if len(recipients) > 3 else ''}
📋 Subject: {subject}
📝 Body length: {len(body)} characters

💾 Email logged to: {log_file if 'log_file' in locals() else 'email log'}

💡 In production mode, this would be sent via SMTP.
   Set environment variable: DEMO_MODE=false for actual sending."""
    
    def _detect_provider(self, email: str) -> str:
        """Detect email provider from address"""
        domain = email.split('@')[1].lower()
        
        if 'gmail' in domain:
            return 'gmail'
        elif 'outlook' in domain or 'hotmail' in domain:
            return 'outlook'
        elif 'yahoo' in domain:
            return 'yahoo'
        elif 'office365' in domain:
            return 'office365'
        else:
            return 'gmail'  # Default to Gmail settings
    
    def _attach_file(self, message: MIMEMultipart, file_path: str):
        """Attach file to email message"""
        try:
            with open(file_path, 'rb') as file:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file.read())
            
            encoders.encode_base64(part)
            
            filename = os.path.basename(file_path)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            message.attach(part)
            
        except Exception as e:
            logger.error(f"Error attaching file {file_path}: {e}")
    
    def _log_sent_email(self, sender: str, recipients: List[str], subject: str):
        """Log sent email for tracking"""
        log_entry = {
            'timestamp': datetime.now(),
            'sender': sender,
            'recipients_count': len(recipients),
            'subject': subject
        }
        self.sent_emails_log.append(log_entry)
    
    def send_bulk_email(self, sender_email: str, password: str,
                       recipient_groups: Dict[str, List[str]],
                       subject_template: str, body_template: str,
                       personalize: bool = True) -> str:
        """
        Send bulk emails with optional personalization
        
        Args:
            sender_email: Sender's email
            password: App password
            recipient_groups: Dict of group_name -> [emails]
            subject_template: Subject with {variables}
            body_template: Body with {variables}
            personalize: Whether to personalize each email
        
        Returns:
            Summary of bulk send operation
        """
        
        total_sent = 0
        total_failed = 0
        results = []
        
        for group_name, recipients in recipient_groups.items():
            for recipient in recipients:
                try:
                    # Personalize if needed
                    if personalize:
                        recipient_name = recipient.split('@')[0].title()
                        subject = subject_template.format(name=recipient_name, group=group_name)
                        body = body_template.format(name=recipient_name, group=group_name)
                    else:
                        subject = subject_template
                        body = body_template
                    
                    # Send individual email
                    result = self.send_email(
                        sender_email, password, [recipient],
                        subject, body
                    )
                    
                    if '✅' in result:
                        total_sent += 1
                    else:
                        total_failed += 1
                        results.append(f"Failed: {recipient}")
                        
                except Exception as e:
                    total_failed += 1
                    results.append(f"Error sending to {recipient}: {str(e)}")
        
        summary = f"""📊 BULK EMAIL SUMMARY:

✅ Successfully sent: {total_sent}
❌ Failed: {total_failed}
📧 Total recipients: {total_sent + total_failed}
"""
        
        if results:
            summary += "\n⚠️  Issues:\n" + "\n".join(results[:5])
            if len(results) > 5:
                summary += f"\n... and {len(results) - 5} more"
        
        return summary
    
    def get_email_statistics(self) -> Dict:
        """Get email sending statistics"""
        
        if not self.sent_emails_log:
            return {
                "total_sent": 0,
                "today_sent": 0,
                "most_recent": None
            }
        
        today = datetime.now().date()
        today_count = sum(1 for log in self.sent_emails_log 
                         if log['timestamp'].date() == today)
        
        most_recent = max(self.sent_emails_log, key=lambda x: x['timestamp'])
        
        return {
            "total_sent": len(self.sent_emails_log),
            "today_sent": today_count,
            "most_recent": {
                "subject": most_recent['subject'],
                "recipients": most_recent['recipients_count'],
                "time": most_recent['timestamp'].strftime('%I:%M %p')
            }
        }
    
    def create_html_email(self, title: str, content: str, 
                         footer: str = None) -> str:
        """Create professional HTML email template"""
        
        if not footer:
            footer = f"""
            <p style='color: #666; font-size: 12px; margin-top: 30px;'>
                Sent by Academic AI Assistant<br>
                {datetime.now().strftime('%d %B %Y, %I:%M %p')}
            </p>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;'>
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;'>
                <h1 style='color: white; margin: 0; font-size: 24px;'>{title}</h1>
            </div>
            <div style='background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;'>
                {content}
                <hr style='border: none; border-top: 1px solid #ddd; margin: 30px 0;'>
                {footer}
            </div>
        </body>
        </html>
        """
        
        return html