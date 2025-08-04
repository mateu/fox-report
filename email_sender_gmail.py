#!/usr/bin/env python3
"""
Patched version with enhanced SMTP debugging
"""

import os
import sys
import json
import tempfile
import subprocess
import re
import logging
import shutil
import smtplib
from datetime import datetime
from typing import Dict, Optional, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from jinja2 import Environment, FileSystemLoader, Template
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging using lazy formatting approach
logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Custom exception for email sending errors."""
    pass


class EmailSender:
    """Handles email template rendering and sending via Gmail SMTP or system mail."""
    
    def __init__(self, config: Dict):
        """
        Initialize EmailSender with configuration.
        
        Args:
            config: Configuration dictionary with email settings
        """
        self.config = config
        self.email_config = config.get('email', {})
        self.recipient = self.email_config.get('recipient', 'hunter@406mt.org')
        self.format_type = self.email_config.get('format', 'html')
        
        # SMTP configuration
        self.smtp_config = self.email_config.get('smtp', {})
        self.use_smtp = self.smtp_config.get('enabled', False)
        
        # Set up Jinja2 environment for template rendering
        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader('.'),
                autoescape=True if self.format_type == 'html' else False
            )
        except Exception as e:
            logger.error("Failed to initialize Jinja2 environment: %s", str(e))
            raise EmailSendError("Template system initialization failed") from e

    def _check_smtp_config(self) -> Tuple[bool, str]:
        """
        Check if SMTP configuration is valid.
        
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not self.use_smtp:
            return False, "SMTP not enabled"
            
        required_fields = ['server', 'port', 'username']
        missing_fields = [field for field in required_fields 
                         if not self.smtp_config.get(field)]
        
        if missing_fields:
            return False, f"Missing SMTP config fields: {', '.join(missing_fields)}"
            
        # Check for password in config or environment
        password = self.smtp_config.get('password') or os.getenv('GMAIL_APP_PASSWORD')
        if not password:
            return False, "No SMTP password found in config or GMAIL_APP_PASSWORD environment variable"
            
        return True, ""

    def _send_via_smtp(self, subject: str, body: str, json_report_path: str = None) -> Tuple[bool, str, str]:
        """
        Send email via Gmail SMTP with enhanced debugging.
        
        Args:
            subject: Email subject
            body: Email body content
            json_report_path: Path to JSON report file for attachment
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        # Create unique debug file path for this attempt
        debug_file_path = os.path.join(
            tempfile.gettempdir(), 
            f"smtp_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        try:
            # Get password from config or environment
            password = self.smtp_config.get('password') or os.getenv('GMAIL_APP_PASSWORD')
            
            # Log SMTP configuration (without password)
            logger.debug("SMTP Configuration - Server: %s, Port: %s, Username: %s, TLS: %s", 
                        self.smtp_config['server'], 
                        self.smtp_config['port'],
                        self.smtp_config['username'],
                        self.smtp_config.get('use_tls', True))
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['username']
            msg['To'] = self.recipient
            msg['Subject'] = subject
            
            # Add body
            if self.format_type == 'html':
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Add JSON attachment if provided
            if json_report_path and os.path.exists(json_report_path):
                try:
                    with open(json_report_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(json_report_path)}'
                    )
                    msg.attach(part)
                    logger.debug("Attached JSON report: %s", json_report_path)
                except Exception as e:
                    logger.warning("Failed to attach JSON report: %s", str(e))
            
            # Write full message to debug file BEFORE sending
            full_message = msg.as_string()
            try:
                with open(debug_file_path, 'w', encoding='utf-8') as debug_file:
                    debug_file.write("=== SMTP DEBUG LOG ===\n")
                    debug_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    debug_file.write(f"Server: {self.smtp_config['server']}\n")
                    debug_file.write(f"Port: {self.smtp_config['port']}\n")
                    debug_file.write(f"Username: {self.smtp_config['username']}\n")
                    debug_file.write(f"Recipient: {self.recipient}\n")
                    debug_file.write(f"Use TLS: {self.smtp_config.get('use_tls', True)}\n")
                    debug_file.write("=== FULL EMAIL MESSAGE ===\n")
                    debug_file.write(full_message)
                    debug_file.write("\n=== SMTP TRANSACTION LOG ===\n")
                
                logger.info("Full email message written to debug file: %s", debug_file_path)
            except Exception as e:
                logger.warning("Failed to write debug file: %s", str(e))
            
            # SMTP Connection and Transaction with verbose logging
            server = None
            try:
                # Step 1: Connect to SMTP server
                logger.info("Attempting SMTP connection to %s:%s", 
                           self.smtp_config['server'], self.smtp_config['port'])
                
                server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
                
                # Enable debug output to capture SMTP protocol conversation
                server.set_debuglevel(1)
                
                logger.info("SMTP connection established successfully to %s:%s", 
                           self.smtp_config['server'], self.smtp_config['port'])
                
                # Step 2: Start TLS if configured
                if self.smtp_config.get('use_tls', True):
                    logger.info("Starting TLS encryption")
                    tls_response = server.starttls()
                    logger.info("TLS started - Response code: %s, Message: %s", 
                               tls_response[0], tls_response[1].decode('utf-8') if tls_response[1] else 'None')
                else:
                    logger.info("TLS disabled in configuration")
                
                # Step 3: Authenticate
                logger.info("Attempting SMTP authentication for user: %s", self.smtp_config['username'])
                
                try:
                    login_response = server.login(self.smtp_config['username'], password)
                    logger.info("SMTP authentication successful - Response code: %s, Message: %s", 
                               login_response[0], login_response[1].decode('utf-8') if login_response[1] else 'None')
                except smtplib.SMTPAuthenticationError as auth_error:
                    logger.error("SMTP authentication failed - Code: %s, Message: %s", 
                                auth_error.smtp_code, auth_error.smtp_error.decode('utf-8') if auth_error.smtp_error else 'None')
                    raise
                except Exception as auth_error:
                    logger.error("SMTP authentication error: %s", str(auth_error))
                    raise
                
                # Step 4: Send email
                logger.info("Sending email from %s to %s", self.smtp_config['username'], self.recipient)
                
                try:
                    send_result = server.sendmail(self.smtp_config['username'], self.recipient, full_message)
                    
                    # sendmail() returns a dictionary of failed recipients
                    if send_result:
                        # Some recipients failed
                        logger.warning("Some recipients failed: %s", send_result)
                        failed_recipients = list(send_result.keys())
                        logger.error("Failed to send to recipients: %s", ', '.join(failed_recipients))
                        raise EmailSendError(f"Failed to send to: {', '.join(failed_recipients)}")
                    else:
                        # All recipients succeeded
                        logger.info("Email sent successfully to all recipients")
                        
                        # Log successful send to debug file
                        try:
                            with open(debug_file_path, 'a', encoding='utf-8') as debug_file:
                                debug_file.write(f"\n=== SEND RESULT ===\n")
                                debug_file.write(f"Success: True\n")
                                debug_file.write(f"Failed recipients: None\n")
                                debug_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
                        except Exception as e:
                            logger.warning("Failed to update debug file with send result: %s", str(e))
                            
                except smtplib.SMTPRecipientsRefused as recipients_error:
                    logger.error("All recipients refused - Error: %s", recipients_error.recipients)
                    raise
                except smtplib.SMTPSenderRefused as sender_error:
                    logger.error("Sender refused - Code: %s, Message: %s, Sender: %s", 
                                sender_error.smtp_code, sender_error.smtp_error.decode('utf-8') if sender_error.smtp_error else 'None', sender_error.sender)
                    raise
                except smtplib.SMTPDataError as data_error:
                    logger.error("SMTP data error - Code: %s, Message: %s", 
                                data_error.smtp_code, data_error.smtp_error.decode('utf-8') if data_error.smtp_error else 'None')
                    raise
                except Exception as send_error:
                    logger.error("Email send error: %s", str(send_error))
                    raise
                
                # Step 5: Clean disconnect
                logger.info("Closing SMTP connection")
                server.quit()
                logger.info("SMTP connection closed successfully")
                
            except Exception as smtp_error:
                # Log error to debug file
                try:
                    with open(debug_file_path, 'a', encoding='utf-8') as debug_file:
                        debug_file.write(f"\n=== ERROR ===\n")
                        debug_file.write(f"Error: {str(smtp_error)}\n")
                        debug_file.write(f"Error type: {type(smtp_error).__name__}\n")
                        debug_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
                except Exception as e:
                    logger.warning("Failed to write error to debug file: %s", str(e))
                
                # Ensure server connection is closed
                if server:
                    try:
                        server.quit()
                        logger.info("SMTP connection closed after error")
                    except Exception as close_error:
                        logger.warning("Error closing SMTP connection: %s", str(close_error))
                
                raise smtp_error
            
            success_msg = f"Email sent successfully via SMTP to {self.recipient}"
            logger.info(success_msg)
            return True, success_msg, ""
            
        except Exception as e:
            error_msg = f"SMTP send failed: {str(e)}"
            logger.error(error_msg)
            logger.info("Debug information written to: %s", debug_file_path)
            return False, "", error_msg

    def _check_mail_command_availability(self) -> Tuple[bool, str]:
        """Check if a mail command is available on the system."""
        mail_commands = ['mail', 'mailx', 'sendmail']
        
        for cmd in mail_commands:
            if shutil.which(cmd):
                logger.debug("Found mail command: %s", cmd)
                return True, cmd
        
        logger.warning("No mail command found on system")
        return False, ""

    def _send_via_system_mail(self, subject: str, body: str, json_report_path: str = None) -> Tuple[bool, str, str]:
        """
        Send email via system mail command (fallback).

        Args:
            subject: Email subject
            body: Email body content  
            json_report_path: Path to JSON report file for attachment
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        # Check if mail command is available
        mail_available, mail_cmd = self._check_mail_command_availability()
        if not mail_available:
            error_msg = "No mail command found on system. Please install mailutil, mailx, or similar package."
            logger.error(error_msg)
            return False, "", error_msg

        try:
            # Prepare mail command
            if json_report_path and os.path.exists(json_report_path):
                # Send with attachment
                cmd = [
                    mail_cmd,
                    '-s', subject,
                    '-a', json_report_path,
                    self.recipient
                ]
            else:
                # Send without attachment
                cmd = [
                    mail_cmd, 
                    '-s', subject,
                    self.recipient
                ]
            
            logger.debug("Executing mail command: %s", ' '.join(cmd))
            
            # Execute mail command
            result = subprocess.run(
                cmd,
                input=body,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                success_msg = f"Email sent successfully via system mail to {self.recipient}"
                logger.info(success_msg)
                return True, result.stdout, result.stderr
            else:
                error_msg = f"Mail command failed (exit {result.returncode}): {result.stderr}"
                logger.error(error_msg)
                return False, result.stdout, error_msg
                
        except subprocess.TimeoutExpired:
            error_msg = "Mail command timed out after 30 seconds"
            logger.error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Failed to execute mail command: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

    def _generate_subject(self) -> str:
        """Generate email subject line."""
        current_date = datetime.now().strftime('%Y-%m-%d')
        return f"Fox Detection Report - {current_date}"

    def render_email_body(self, report: Dict, markdown_content: str) -> str:
        """
        Render email body from template and report data.
        
        Args:
            report: Report dictionary with metadata and data
            markdown_content: Markdown formatted report content
            
        Returns:
            Rendered email body as string
        """
        if self.format_type == 'html':
            return self._render_html_body(report, markdown_content)
        else:
            return self._render_text_body(report, markdown_content)

    def _render_html_body(self, report: Dict, markdown_content: str) -> str:
        """Render HTML email body."""
        # Convert markdown to HTML (basic conversion)
        html_content = markdown_content.replace('\n', '<br>\n')
        
        # Simple markdown to HTML conversion
        lines = html_content.split('\n')
        converted_lines = []
        
        for line in lines:
            # Headers
            if line.strip().startswith('# '):
                converted_lines.append(f'<h1>{line.strip()[2:]}</h1>')
            elif line.strip().startswith('## '):
                converted_lines.append(f'<h2>{line.strip()[3:]}</h2>')
            elif line.strip().startswith('### '):
                converted_lines.append(f'<h3>{line.strip()[4:]}</h3>')
            # Bold text
            elif '**' in line:
                line = line.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
                converted_lines.append(line)
            # Convert markdown links [text](url) to HTML links
            elif "[" in line and "](" in line and ")" in line:
                # Use regex to convert markdown links to HTML
                line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', line)
                converted_lines.append(line)
            # List items
            elif line.strip().startswith('- '):
                converted_lines.append(f'<li>{line.strip()[2:]}</li>')
            else:
                converted_lines.append(line)
        
        html_content = '\n'.join(converted_lines)
        
        # Create HTML template
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Fox Detection Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }
        .summary { margin: 20px 0; }
        .footer { margin-top: 30px; font-size: 0.9em; color: #666; }
        h1, h2, h3 { color: #333; }
        li { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🦊 Fox Detection Report</h1>
        <p>Generated: {{ generation_time }}</p>
    </div>
    
    <div class="summary">
        {{ content | safe }}
    </div>
    
    <div class="footer">
        <p>This report was automatically generated by the Frigate Fox Detection System.</p>
        <p>Report data is attached as JSON for further analysis.</p>
    </div>
</body>
</html>
        """
        
        template = Template(html_template)
        return template.render(
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            content=html_content
        )

    def _render_text_body(self, report: Dict, markdown_content: str) -> str:
        """Render plain text email body."""
        header = f"🦊 Fox Detection Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        separator = "=" * len(header)
        
        footer = "\n\nThis report was automatically generated by the Frigate Fox Detection System.\nReport data is attached as JSON for further analysis."
        
        return f"{header}\n{separator}\n\n{markdown_content}{footer}"

    def send_email(self, report: Dict, markdown_content: str, 
                   json_report_path: str = None) -> Tuple[bool, str, str]:
        """
        Send email with report content and JSON attachment.
        
        Args:
            report: Report dictionary with metadata and data
            markdown_content: Markdown formatted report content
            json_report_path: Path to JSON report file for attachment
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        logger.info("Preparing to send email to %s", self.recipient)
        
        # Generate subject and body
        subject = self._generate_subject()
        
        try:
            email_body = self.render_email_body(report, markdown_content)
        except Exception as e:
            error_msg = f"Failed to render email body: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

        # Try SMTP first if configured, then fall back to system mail
        if self.use_smtp:
            smtp_valid, smtp_error = self._check_smtp_config()
            if smtp_valid:
                logger.info("Attempting to send via Gmail SMTP")
                success, stdout, stderr = self._send_via_smtp(subject, email_body, json_report_path)
                if success:
                    return success, stdout, stderr
                else:
                    logger.warning("SMTP send failed, falling back to system mail: %s", stderr)
            else:
                logger.warning("SMTP config invalid, using system mail: %s", smtp_error)
        
        # Fall back to system mail
        logger.info("Sending via system mail")
        return self._send_via_system_mail(subject, email_body, json_report_path)


def main():
    """Test the email sender functionality."""
    # Configure logging
    # Set log level based on environment variable
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test configuration
    test_config = {
        'email': {
            'recipient': 'hunter@406mt.org',
            'format': 'html',
            'smtp': {
                'enabled': True,
                'server': 'smtp.gmail.com',
                'port': 587,
                'use_tls': True,
                'username': 'hunter@406mt.org',
                'password': ''  # Will use GMAIL_APP_PASSWORD env var
            }
        }
    }
    
    # Create test report
    test_report = {
        'metadata': {
            'generation_time': datetime.now().isoformat(),
            'nights_analyzed': 1
        },
        'totals': {
            'total_events': 2,
            'cameras_with_detections': 2
        }
    }
    
    test_markdown = """# Fox Detection Summary

**Total Events:** 2
**Cameras with Detections:** 2

## Camera Summary
- **pano**: 1 event
- **court**: 1 event

Both events occurred around 9:59 AM on August 3rd."""
    
    # Test email sending
    try:
        sender = EmailSender(test_config)
        success, stdout, stderr = sender.send_email(test_report, test_markdown)
        
        if success:
            print("✅ Email sent successfully!")
            print(f"Output: {stdout}")
        else:
            print("❌ Email send failed!")
            print(f"Error: {stderr}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
