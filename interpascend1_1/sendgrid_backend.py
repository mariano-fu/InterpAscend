"""
Custom SendGrid email backend that disables click tracking for clean URLs.
"""

import os
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMultiAlternatives
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, TrackingSettings, ClickTracking
from python_http_client.exceptions import HTTPError
import logging

logger = logging.getLogger(__name__)


class SendGridBackend(BaseEmailBackend):
    """
    Custom SendGrid backend that disables click tracking to prevent
    tracking URLs from being added to password reset emails.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY environment variable is required")
        self.client = SendGridAPIClient(api_key=self.api_key)
    
    def send_messages(self, email_messages):
        """
        Send multiple email messages via SendGrid API with tracking disabled.
        """
        if not email_messages:
            return 0
        
        sent_count = 0
        for message in email_messages:
            if self._send_message(message):
                sent_count += 1
        
        return sent_count
    
    def _send_message(self, message):
        """
        Send a single email message via SendGrid API.
        """
        try:
            # Create SendGrid Mail object
            mail = Mail()
            
            # Set basic email properties
            mail.from_email = message.from_email
            mail.subject = message.subject
            
            # Add recipients
            if hasattr(message, 'to') and message.to:
                for recipient in message.to:
                    mail.add_to(recipient)
            
            # Set email content
            if hasattr(message, 'body') and message.body:
                mail.add_content(message.body, "text/plain")
            
            # Add HTML content if available
            if hasattr(message, 'alternatives') and message.alternatives:
                for content, content_type in message.alternatives:
                    if content_type == 'text/html':
                        mail.add_content(content, "text/html")
            
            # CRITICAL: Disable click tracking to prevent tracking URLs
            tracking_settings = TrackingSettings()
            click_tracking = ClickTracking()
            click_tracking.enable = False  # This prevents SendGrid from wrapping URLs
            click_tracking.enable_text = False  # Also disable for plain text
            tracking_settings.click_tracking = click_tracking
            mail.tracking_settings = tracking_settings
            
            # Send the email
            response = self.client.send(mail)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully via SendGrid: {message.subject}")
                return True
            else:
                logger.error(f"SendGrid API returned status {response.status_code}: {response.body}")
                if not self.fail_silently:
                    raise Exception(f"SendGrid API error: {response.status_code}")
                return False
                
        except HTTPError as e:
            logger.error(f"SendGrid HTTP error: {e}")
            if not self.fail_silently:
                raise
            return False
        except Exception as e:
            logger.error(f"Error sending email via SendGrid: {e}")
            if not self.fail_silently:
                raise
            return False