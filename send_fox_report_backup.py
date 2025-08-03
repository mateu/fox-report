#!/usr/bin/env python3
"""
Frigate Fox Report Sender

Main script that generates fox detection reports and sends them via email.
Integrates report generation, JSON export, and email sending functionality.
"""

import os
import sys
import yaml
import json
import logging
from datetime import datetime
from typing import Optional

from report_generator import generate_fox_report, get_last_n_nights_data
from email_sender import send_fox_report_email

# Configure logging using lazy formatting approach (per user rules)
logger = logging.getLogger(__name__)


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
        output_path = f"/tmp/fox_report_{date_str}.json"
    
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
         send_email: bool = True) -> bool:
    """
    Main function to generate and send fox detection report.
    
    Args:
        config_path: Path to configuration file
        nights: Number of nights to analyze
        json_output: Optional custom JSON output path
        send_email: Whether to send email (default: True)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load configuration
        config = load_config(config_path)
        
        # Get nights data
        logger.info("Retrieving data for last %d nights", nights)
        nights_list, dusk_dawn_ranges = get_last_n_nights_data(nights)
        
        if not nights_list:
            logger.error("Could not retrieve time ranges for nights analysis")
            return False
        
        logger.info("Analyzing %d nights of data", len(nights_list))
        for night, (dusk, dawn) in zip(nights_list, dusk_dawn_ranges):
            logger.info("Night %d: %s - %s", night, 
                       dusk.strftime('%Y-%m-%d %H:%M'), 
                       dawn.strftime('%Y-%m-%d %H:%M'))
        
        # Generate report
        logger.info("Generating fox detection report")
        report, markdown_content = generate_fox_report(nights_list, dusk_dawn_ranges)
        
        # Save JSON report
        json_path = save_json_report(report, json_output)
        
        # Send email if requested
        if send_email:
            logger.info("Sending email report")
            success, stdout, stderr = send_fox_report_email(
                config, report, markdown_content, json_path
            )
            
            if success:
                logger.info("Email report sent successfully")
                print("✓ Fox detection report sent successfully!")
                if stdout:
                    logger.debug("Mail stdout: %s", stdout)
                return True
            else:
                logger.error("Failed to send email report")
                logger.error("Mail stderr: %s", stderr)
                print(f"✗ Failed to send email: {stderr}")
                return False
        else:
            logger.info("Email sending skipped (send_email=False)")
            print(f"✓ Report generated successfully. JSON saved to: {json_path}")
            return True
            
    except Exception as e:
        logger.exception("Failed to generate/send report: %s", str(e))
        print(f"✗ Error: {e}")
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
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🦊 Frigate Fox Report Sender")
    print("=" * 40)
    
    # Run main function
    success = main(
        config_path=args.config,
        nights=args.nights,
        json_output=args.output,
        send_email=not args.no_email
    )
    
    sys.exit(0 if success else 1)
