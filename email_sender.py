#!/usr/bin/env python3
"""
Frigate Fox Report Email Sender

This module handles rendering email templates and sending reports via system mail.
It includes support for HTML and text email formats with JSON report attachments.
"""

import os
import sys
import json
import tempfile
import subprocess
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from jinja2 import Environment, FileSystemLoader, Template

# Configure logging using lazy formatting approach (per user rules)
logger = logging.getLogger(__name__)


class EmailSender:
    """Handles email template rendering and sending via system mail."""
    
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
        
        # Set up Jinja2 environment for template rendering
        self.jinja_env = Environment(
            loader=FileSystemLoader('.'),
            autoescape=True if self.format_type == 'html' else False
        )
        
    def _generate_subject(self, report_date: str = None) -> str:
        """
        Generate email subject with date.
        
        Args:
            report_date: Optional date string, defaults to today
            
        Returns:
            Formatted email subject
        """
        if not report_date:
            report_date = datetime.now().strftime('%Y-%m-%d')
        
        return f"Frigate Fox Report – {report_date}"
    
    def _render_html_template(self, report: Dict, markdown_content: str) -> str:
        """
        Render HTML email template.
        
        Args:
            report: Report dictionary with metadata and data
            markdown_content: Markdown formatted report content
            
        Returns:
            Rendered HTML content
        """
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ subject }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #ff6b35;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .fox-emoji {
            font-size: 2em;
            margin-bottom: 10px;
        }
        h1 {
            color: #ff6b35;
            margin: 0;
        }
        .summary {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }
        .stat-box {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #ff6b35;
        }
        .stat-label {
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .report-content {
            margin: 30px 0;
        }
        .report-content pre {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            overflow-x: auto;
            border-left: 4px solid #ff6b35;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
        }
        .attachment-note {
            background: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
        }
        .attachment-note strong {
            color: #1976d2;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="fox-emoji">🦊</div>
            <h1>{{ subject }}</h1>
            <p>Generated on {{ report.metadata.generated_at | replace('T', ' ') | replace('Z', '') }}</p>
        </div>
        
        <div class="summary">
            <h2>Detection Summary</h2>
            <div class="summary-grid">
                <div class="stat-box">
                    <div class="stat-number">{{ report.totals.total_events }}</div>
                    <div class="stat-label">Total Events</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{{ report.totals.cameras_with_detections }}</div>
                    <div class="stat-label">Active Cameras</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{{ report.metadata.total_nights }}</div>
                    <div class="stat-label">Nights Analyzed</div>
                </div>
            </div>
        </div>
        
        <div class="report-content">
            <h2>Detailed Report</h2>
            <pre>{{ markdown_content }}</pre>
        </div>
        
        <div class="attachment-note">
            <strong>📎 Attachment:</strong> Complete JSON report with all detection data is attached to this email.
        </div>
        
        <div class="footer">
            <p>🦊 Frigate Fox Detection System<br>
            Automated report generated from {{ report.metadata.total_nights }} nights of surveillance data</p>
        </div>
    </div>
</body>
</html>
        """
        
        template = Template(html_template)
        subject = self._generate_subject()
        
        return template.render(
            subject=subject,
            report=report,
            markdown_content=markdown_content
        )
    
    def _render_text_template(self, report: Dict, markdown_content: str) -> str:
        """
        Render plain text email template.
        
        Args:
            report: Report dictionary with metadata and data
            markdown_content: Markdown formatted report content
            
        Returns:
            Rendered text content
        """
        text_template = """🦊 {{ subject }}
================================================================

Generated: {{ report.metadata.generated_at }}
Nights Analyzed: {{ report.metadata.total_nights }}

DETECTION SUMMARY
================================================================
Total Events: {{ report.totals.total_events }}
Cameras with Detections: {{ report.totals.cameras_with_detections }}

DETAILED REPORT
================================================================
{{ markdown_content }}

================================================================
📎 ATTACHMENT: Complete JSON report with all detection data
🦊 Frigate Fox Detection System - Automated Report
================================================================
        """
        
        template = Template(text_template)
        subject = self._generate_subject()
        
        return template.render(
            subject=subject,
            report=report,
            markdown_content=markdown_content
        )
    
    def render_email_body(self, report: Dict, markdown_content: str) -> str:
        """
        Render email body based on configured format.
        
        Args:
            report: Report dictionary with metadata and data
            markdown_content: Markdown formatted report content
            
        Returns:
            Rendered email body content
        """
        logger.info("Rendering email body in %s format", self.format_type)
        
        if self.format_type.lower() == 'html':
            return self._render_html_template(report, markdown_content)
        else:
            return self._render_text_template(report, markdown_content)
    
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
        
        # Generate subject
        subject = self._generate_subject()
        
        # Render email body
        email_body = self.render_email_body(report, markdown_content)
        
        # Create temporary file for email body if needed
        body_file = None
        try:
            # Write email body to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html' if self.format_type == 'html' else '.txt', 
                                             delete=False) as f:
                f.write(email_body)
                body_file = f.name
            
            # Prepare mail command
            mail_cmd = ['mail', '-s', subject]
            
            # Add attachment if JSON report provided
            if json_report_path and os.path.exists(json_report_path):
                mail_cmd.extend(['-A', json_report_path])
                logger.info("Attaching JSON report: %s", json_report_path)
            
            # Add recipient
            mail_cmd.append(self.recipient)
            
            logger.info("Executing mail command: %s", ' '.join(mail_cmd))
            
            # Execute mail command with email body as input
            with open(body_file, 'r') as body_input:
                result = subprocess.run(
                    mail_cmd,
                    stdin=body_input,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            success = result.returncode == 0
            stdout = result.stdout
            stderr = result.stderr
            
            if success:
                logger.info("Email sent successfully to %s", self.recipient)
            else:
                logger.error("Failed to send email. Return code: %d", result.returncode)
                logger.error("STDERR: %s", stderr)
            
            return success, stdout, stderr
            
        except subprocess.TimeoutExpired:
            error_msg = "Mail command timed out after 30 seconds"
            logger.error(error_msg)
            return False, "", error_msg
            
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg
            
        finally:
            # Clean up temporary body file
            if body_file and os.path.exists(body_file):
                try:
                    os.unlink(body_file)
                except OSError:
                    pass  # Ignore cleanup errors


def send_fox_report_email(config: Dict, report: Dict, markdown_content: str, 
                         json_report_path: str = None) -> Tuple[bool, str, str]:
    """
    Convenience function to send fox report email.
    
    Args:
        config: Configuration dictionary
        report: Report dictionary with metadata and data
        markdown_content: Markdown formatted report content
        json_report_path: Path to JSON report file for attachment
        
    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
    sender = EmailSender(config)
    return sender.send_email(report, markdown_content, json_report_path)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🦊 Frigate Fox Email Sender Test")
    print("=" * 40)
    
    # Load configuration
    try:
        import yaml
        with open('config_template.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error("Failed to load config: %s", str(e))
        print(f"✗ Could not load configuration: {e}")
        sys.exit(1)
    
    # Create test report data
    test_report = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'nights_analyzed': [1, 2, 3],
            'total_nights': 3
        },
        'totals': {
            'total_events': 15,
            'cameras_with_detections': 3
        }
    }
    
    test_markdown = """## Fox Detection Report

### Summary
- **Total Events**: 15
- **Cameras Active**: 3
- **Peak Activity**: Night 2 (8 events)

### Camera Breakdown
- **Front Door**: 6 events
- **Backyard**: 5 events  
- **Side Gate**: 4 events

### Recommendations
All cameras showing good fox activity. Consider adjusting motion sensitivity on Front Door camera.
    """
    
    print("Testing email rendering and sending...")
    
    try:
        sender = EmailSender(config)
        
        # Test HTML rendering
        html_body = sender.render_email_body(test_report, test_markdown)
        print("✓ HTML template rendered successfully")
        
        # Test text rendering
        sender.format_type = 'text'
        text_body = sender.render_email_body(test_report, test_markdown)
        print("✓ Text template rendered successfully")
        
        print(f"\nRecipient: {sender.recipient}")
        print(f"Subject: {sender._generate_subject()}")
        
        # Note: Actual sending is commented out to avoid spam during testing
        # Uncomment the following lines to test actual email sending:
        
        # success, stdout, stderr = sender.send_email(test_report, test_markdown)
        # if success:
        #     print("✓ Test email sent successfully!")
        # else:
        #     print(f"✗ Failed to send email: {stderr}")
        
        print("✓ Email sender implementation ready")
        
    except Exception as e:
        logger.exception("Test failed: %s", str(e))
        print(f"✗ Test failed: {e}")
        sys.exit(1)
