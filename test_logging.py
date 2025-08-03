#!/usr/bin/env python3
"""
Test script to demonstrate logging configuration with lazy formatting.
"""

import tempfile
import os
from send_fox_report import setup_logging
import logging

def test_logging_features():
    """Test the enhanced logging system."""
    
    # Test configuration
    test_config = {
        'output': {
            'log_file': '/tmp/test_fox_logging.log',
            'use_syslog': True
        }
    }
    
    print("🧪 Testing Enhanced Logging System")
    print("=" * 40)
    
    # Test 1: Normal logging
    print("\n1. Testing normal logging level...")
    setup_logging(verbose=False, quiet=False, config=test_config)
    logger = logging.getLogger('test_normal')
    
    logger.debug("This debug message should NOT appear in normal mode")
    logger.info("This info message should appear: %d events processed", 42)
    logger.warning("This warning should appear: %s", "test warning")
    logger.error("This error should appear: %s", "test error")
    
    # Test 2: Verbose logging  
    print("\n2. Testing verbose logging level...")
    setup_logging(verbose=True, quiet=False, config=test_config)
    logger = logging.getLogger('test_verbose')
    
    logger.debug("This debug message SHOULD appear in verbose mode: %s", "debug info")
    logger.info("Found %d fox events", 15)
    
    # Test 3: Quiet logging
    print("\n3. Testing quiet logging level...")
    setup_logging(verbose=False, quiet=True, config=test_config)
    logger = logging.getLogger('test_quiet')
    
    logger.debug("This debug should NOT appear in quiet mode")
    logger.info("This info should NOT appear in quiet mode")
    logger.warning("This warning SHOULD appear in quiet mode: %s", "important warning")
    logger.error("This error SHOULD appear in quiet mode: %s", "critical error")
    
    # Check log file
    print("\n4. Checking log file contents...")
    if os.path.exists('/tmp/test_fox_logging.log'):
        with open('/tmp/test_fox_logging.log', 'r') as f:
            log_content = f.read()
        print(f"Log file size: {len(log_content)} characters")
        print("Last few log entries:")
        print(log_content.split('\n')[-6:-1])
    else:
        print("Log file not found!")
    
    print("\n✓ Logging system test completed!")
    print("✓ Features demonstrated:")
    print("  - Lazy formatting (no f-strings in logging calls)")
    print("  - Rotating file handler (/tmp/test_fox_logging.log)")
    print("  - Syslog integration")
    print("  - --verbose/--quiet flag support")
    print("  - Multiple log levels")

if __name__ == "__main__":
    test_logging_features()
