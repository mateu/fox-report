#!/usr/bin/env python3
"""
Frigate Fox Report Sender

Main script that generates fox detection reports and sends them via email.
Integrates report generation, JSON export, and email sending functionality.
"""

import copy
import json
import logging
import logging.handlers
import sys
from datetime import datetime

import yaml
from dotenv import load_dotenv

from fox_report.config import settings
from fox_report.email.sender import EmailSender
from fox_report.report_generator import generate_fox_report, get_last_n_nights_data

# Load environment variables from .env file
load_dotenv()

# Global logger instance
logger = logging.getLogger(__name__)


def setup_logging(
    verbose: bool = False, quiet: bool = False, config: dict | None = None
) -> None:
    """
    Configure logging with rotating file handler and optional syslog.

    Args:
        verbose: Enable DEBUG level logging
        quiet: Enable only ERROR level logging
        config: Configuration dictionary with logging settings
    """
    # Get log level from verbose/quiet flags
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with enhanced formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Enhanced formatter with more context
    if verbose:
        # Detailed format for verbose mode
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # Clean format for normal operation
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional file handler with rotation
    if config and "logging" in config:
        log_config = config["logging"]
        log_file = log_config.get("file_path", "/tmp/fox_report.log")
        max_bytes = log_config.get("max_file_size", 5 * 1024 * 1024)  # 5MB default
        backup_count = log_config.get("backup_count", 3)

        try:
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count
            )
            file_handler.setLevel(logging.DEBUG)  # Always debug level for files

            # File gets detailed format
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

            logger.info("File logging enabled: %s", log_file)

        except (OSError, PermissionError) as e:
            # Fallback to console if file logging fails
            print(f"Warning: Could not setup file logging ({e!s}), using console only")

    # Setup syslog handler if requested
    if config and config.get("logging", {}).get("use_syslog", False):
        try:
            syslog_handler = logging.handlers.SysLogHandler(address="/dev/log")
            syslog_handler.setLevel(logging.INFO)  # Usually INFO+ for syslog

            # Syslog format (no timestamps, syslog adds them)
            syslog_formatter = logging.Formatter(
                "fox-report[%(process)d]: %(levelname)s - %(funcName)s - %(message)s"
            )
            syslog_handler.setFormatter(syslog_formatter)
            root_logger.addHandler(syslog_handler)

            logger.info("Syslog logging enabled")

        except (FileNotFoundError, ConnectionRefusedError, PermissionError) as e:
            logger.warning("Could not setup syslog handler: %s", str(e))

    # Log the logging configuration
    if verbose:
        logger.debug("Logging configured - Level: %s", logging.getLevelName(log_level))
        logger.debug("Active handlers: %d", len(root_logger.handlers))
        for i, handler in enumerate(root_logger.handlers):
            logger.debug(
                "  Handler %d: %s (level: %s)", i, type(handler).__name__, handler.level
            )


def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        logger.info("Configuration loaded from %s", config_path)
        return config
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", config_path)
        raise
    except yaml.YAMLError as e:
        logger.error("Error parsing configuration file: %s", str(e))
        raise
    except Exception as e:
        logger.error("Error loading configuration: %s", str(e))
        raise


def save_json_report(report: dict, output_path: str | None = None) -> str:
    """
    Save report to JSON file (without thumbnails to reduce size).

    Args:
        report: Report dictionary to save
        output_path: Path for output file (optional)

    Returns:
        Path to saved JSON file
    """
    # Generate default filename if not provided
    if not output_path:
        date_str = datetime.now(tz=settings.tz).strftime("%Y%m%d")
        output_path = f"/tmp/fox_report_{date_str}.json"

    try:
        # Create a copy without thumbnails for JSON export
        json_report = copy.deepcopy(report)

        # Remove thumbnail data to keep file size manageable
        if "events" in json_report:
            for event in json_report["events"]:
                if "thumbnail_data" in event:
                    del event["thumbnail_data"]

        # Save to JSON file with nice formatting
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(json_report, f, indent=2, default=str, ensure_ascii=False)

        logger.info("JSON report saved to: %s", output_path)
        return output_path

    except Exception as e:
        logger.error("Failed to save JSON report: %s", str(e))
        raise


def main(
    config_path: str = "config/template.yaml",
    nights: int = 3,
    json_output: str | None = None,
    send_email: bool = True,
    verbose: bool = False,
    quiet: bool = False,
) -> bool:
    """
    Main execution function.

    Args:
        config_path: Path to configuration file
        nights: Number of nights to analyze
        json_output: Path for JSON output file
        send_email: Whether to send email
        verbose: Enable verbose logging
        quiet: Enable quiet mode

    Returns:
        True if successful, False otherwise
    """
    try:
        # Load configuration and setup logging
        config = load_config(config_path)
        setup_logging(verbose, quiet, config)

        logger.info("Starting fox report generation for %d nights", nights)

        # Get nights data using report generator
        nights_list, dusk_dawn_ranges = get_last_n_nights_data(nights)

        if not nights_list:
            logger.error("Failed to get night data")
            return False

        logger.info("Analyzing %d nights of data", len(nights_list))
        for _i, (night, (dusk, dawn)) in enumerate(
            zip(nights_list, dusk_dawn_ranges, strict=False)
        ):
            logger.debug(
                "Night %d: %s - %s",
                night,
                dusk.strftime("%Y-%m-%d %H:%M"),
                dawn.strftime("%Y-%m-%d %H:%M"),
            )

        # Generate report
        report, markdown = generate_fox_report(nights_list, dusk_dawn_ranges)

        logger.info("Report generated successfully")
        logger.info("Total events found: %d", len(report.get("events", [])))

        # Save JSON report
        json_path = save_json_report(report, json_output)

        # Send email if requested
        if send_email:
            logger.info("Attempting to send email...")

            try:
                email_sender = EmailSender(config)
                success, success_msg, error_msg = email_sender.send_email(
                    report, markdown, json_path
                )

                if success:
                    logger.info("Email sent successfully")
                    if success_msg and not quiet:
                        print(f"✓ Email sent: {success_msg}")
                    return True
                else:
                    logger.error("Failed to send email: %s", error_msg)
                    if error_msg and not quiet:
                        print(f"✗ Failed to send email: {error_msg}")
                    return False

            except Exception as e:
                logger.exception("Email sending failed: %s", str(e))
                stderr = str(e)
                logger.error("Mail stderr: %s", stderr)
                if not quiet:
                    print(f"✗ Failed to send email: {stderr}")
                return False
        else:
            logger.info("Email sending skipped (send_email=False)")
            if not quiet:
                print(f"✓ Report generated successfully. JSON saved to: {json_path}")
            return True

    except Exception as e:
        logger.exception("Failed to generate/send report: %s", str(e))
        if not quiet:
            print(f"✗ Error: {e!s}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate and send fox detection reports"
    )
    parser.add_argument(
        "--config",
        default="config/template.yaml",
        help="Configuration file path (default: config/template.yaml)",
    )
    parser.add_argument(
        "--nights",
        type=int,
        default=3,
        help="Number of nights to analyze (default: 3)",
    )
    parser.add_argument("--json-output", help="Path for JSON output file (optional)")
    parser.add_argument("--no-email", action="store_true", help="Skip sending email")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Enable quiet mode")

    args = parser.parse_args()

    # Run main function
    success = main(
        config_path=args.config,
        nights=args.nights,
        json_output=args.json_output,
        send_email=not args.no_email,
        verbose=args.verbose,
        quiet=args.quiet,
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)
