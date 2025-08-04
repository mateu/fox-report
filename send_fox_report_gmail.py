#!/usr/bin/env python3
"""
Frigate Fox Report Sender

Main script that generates fox detection reports and sends them via email.
Integrates report generation, JSON export, and email sending functionality.
"""

import os
import sys
import yaml

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import json
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

from report_generator import generate_fox_report, get_last_n_nights_data
from email_sender_gmail import EmailSender

# Global logger instance
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, quiet: bool = False, config: dict = None) -> None:
    """
    Configure logging with rotating file handler and optional syslog.
    Uses lazy formatting approach as per user rules.
    
    Args:
        verbose: Enable verbose logging (DEBUG level)
        quiet: Enable quiet mode (WARNING level only)
        config: Configuration dictionary containing logging settings
    """
    # Determine log level based on flags
    if quiet:
        log_level = logging.WARNING
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    # Get log file path from config or use default
    log_file = None
    use_syslog = False
    
    if config and 'output' in config:
        log_file = config['output'].get('log_file', '/tmp/fox_report.log')
        use_syslog = config['output'].get('use_syslog', False)
    else:
        log_file = '/tmp/fox_report.log'
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter using lazy formatting style
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup rotating file handler
    if log_file:
        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Rotating file handler (10MB max, 5 backups)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            logger.info("Logging configured with rotating file handler: %s", log_file)
            
        except Exception as e:
            # Fallback to console if file logging fails
            print("Warning: Could not setup file logging (%s), using console only" % str(e))
    
    # Setup syslog handler if requested
    if use_syslog:
        try:
            syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
            syslog_formatter = logging.Formatter(
                'fox_report[%(process)d]: %(levelname)s - %(message)s'
            )
            syslog_handler.setFormatter(syslog_formatter)
            syslog_handler.setLevel(log_level)
            root_logger.addHandler(syslog_handler)
            
            logger.info("Syslog logging enabled")
            
        except Exception as e:
            logger.warning("Could not setup syslog handler: %s", str(e))
    
    # Always add console handler for immediate feedback (unless quiet mode)
    if not quiet:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO if not verbose else logging.DEBUG)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)


def load_config(config_path: str = 'config_template.yaml') -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info("Configuration loaded from %s", config_path)
        return config
    except Exception as e:
        logger.error("Failed to load configuration from %s: %s", config_path, str(e))
        raise


def save_json_report(report: dict, output_path: str = None) -> str:
    """
    Save report to JSON file.
    
    Args:
        report: Report dictionary to save
        output_path: Optional custom output path
        
    Returns:
        Path to saved JSON file
    """
    if not output_path:
        date_str = datetime.now().strftime('%Y%m%d')
        output_path = "/tmp/fox_report_%s.json" % date_str
    
    try:
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info("JSON report saved to %s", output_path)
        return output_path
        
    except Exception as e:
        logger.error("Failed to save JSON report to %s: %s", output_path, str(e))
        raise


def main(config_path: str = 'config_template.yaml', 
         nights: int = 3,
         json_output: str = None,
         send_email: bool = True,
         verbose: bool = False,
         quiet: bool = False) -> bool:
    """
    Main function to generate and send fox detection report.
    
    Args:
        config_path: Path to configuration file
        nights: Number of nights to analyze
        json_output: Optional custom JSON output path
        send_email: Whether to send email (default: True)
        verbose: Enable verbose logging
        quiet: Enable quiet mode
        
    Returns:
        True if successful, False otherwise
    """
    config = None
    
    try:
        # Load configuration first (before setting up logging)
        config = load_config(config_path)
        
        # Setup logging with configuration
        setup_logging(verbose=verbose, quiet=quiet, config=config)
        
        logger.info("Starting fox detection report generation")
        logger.debug("Configuration: nights=%d, send_email=%s", nights, send_email)
        
        # Get nights data
        logger.info("Retrieving data for last %d nights", nights)
        nights_list, dusk_dawn_ranges = get_last_n_nights_data(nights)
        
        if not nights_list:
            logger.error("Could not retrieve time ranges for nights analysis")
            return False
        
        logger.info("Analyzing %d nights of data", len(nights_list))
        for i, (night, (dusk, dawn)) in enumerate(zip(nights_list, dusk_dawn_ranges)):
            logger.debug("Night %d: %s - %s", night, 
                        dusk.strftime('%Y-%m-%d %H:%M'), 
                        dawn.strftime('%Y-%m-%d %H:%M'))
        
        # Generate report
        logger.info("Generating fox detection report")
        report, markdown_content = generate_fox_report(nights_list, dusk_dawn_ranges)
        
        # Log summary statistics
        fox_events = report.get('totals', {}).get('total_events', 0)
        logger.info("Found %d fox events in report", fox_events)
        
        # Save JSON report
        json_path = save_json_report(report, json_output)
        
        # Send email if requested
        if send_email:
            logger.info("Sending email report")
            try:
                email_sender = EmailSender(config)
                success, stdout, stderr = email_sender.send_email(
                    report, markdown_content, json_path
                )
            except Exception as e:
                success, stdout, stderr = False, "", str(e)
            
            if success:
                logger.info("Email report sent successfully")
                if not quiet:
                    print("✓ Fox detection report sent successfully!")
                if stdout:
                    logger.debug("Mail stdout: %s", stdout)
                return True
            else:
                logger.error("Failed to send email report")
                logger.error("Mail stderr: %s", stderr)
                if not quiet:
                    print("✗ Failed to send email: %s" % stderr)
                return False
        else:
            logger.info("Email sending skipped (send_email=False)")
            if not quiet:
                print("✓ Report generated successfully. JSON saved to: %s" % json_path)
            return True
            
    except Exception as e:
        logger.exception("Failed to generate/send report: %s", str(e))
        if not quiet:
            print("✗ Error: %s" % str(e))
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate and send Frigate Fox detection reports"
    )
    parser.add_argument(
        '--config', '-c',
        default='config_template.yaml',
        help='Configuration file path (default: config_template.yaml)'
    )
    parser.add_argument(
        '--nights', '-n',
        type=int,
        default=3,
        help='Number of nights to analyze (default: 3)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Custom JSON output file path'
    )
    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Generate report but do not send email'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Enable quiet mode (WARNING level only, minimal console output)'
    )
    
    args = parser.parse_args()
    
    # Validate mutually exclusive flags
    if args.verbose and args.quiet:
        print("Error: --verbose and --quiet are mutually exclusive")
        sys.exit(1)
    
    if not args.quiet:
        print("🦊 Frigate Fox Report Sender")
        print("=" * 40)
    
    # Run main function
    success = main(
        config_path=args.config,
        nights=args.nights,
        json_output=args.output,
        send_email=not args.no_email,
        verbose=args.verbose,
        quiet=args.quiet
    )
    
    sys.exit(0 if success else 1)
