#!/usr/bin/env python3
"""
Test script for main orchestration functionality
"""

import subprocess
import sys
import os

def run_command(cmd):
    """Run command and return (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def test_help():
    """Test help output"""
    print("Testing help output...")
    exit_code, stdout, stderr = run_command("python3 send_fox_report_gmail.py --help")
    assert exit_code == 6, f"Expected exit code 6, got {exit_code}"
    assert "Frigate Fox detection reports" in stdout
    assert "Exit Codes:" in stdout
    print("✓ Help output test passed")

def test_mutually_exclusive_args():
    """Test mutually exclusive arguments"""
    print("Testing mutually exclusive arguments...")
    exit_code, stdout, stderr = run_command("python3 send_fox_report_gmail.py --verbose --quiet")
    assert exit_code == 6, f"Expected exit code 6, got {exit_code}"
    assert "mutually exclusive" in stdout
    print("✓ Mutually exclusive args test passed")

def test_invalid_nights():
    """Test invalid nights parameter"""
    print("Testing invalid nights parameter...")
    exit_code, stdout, stderr = run_command("python3 send_fox_report_gmail.py --nights 0")
    assert exit_code == 6, f"Expected exit code 6, got {exit_code}"
    assert "must be positive" in stdout
    print("✓ Invalid nights test passed")

def test_config_not_found():
    """Test configuration file not found"""
    print("Testing config file not found...")
    exit_code, stdout, stderr = run_command("python3 send_fox_report_gmail.py --config nonexistent.yaml --quiet")
    assert exit_code == 1, f"Expected exit code 1, got {exit_code}"
    print("✓ Config not found test passed")

def test_successful_run():
    """Test successful run without email"""
    print("Testing successful run...")
    exit_code, stdout, stderr = run_command("python3 send_fox_report_gmail.py --no-email --quiet")
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
    # Check that JSON file was created
    json_files = [f for f in os.listdir('/tmp') if f.startswith('fox_report_') and f.endswith('.json')]
    assert len(json_files) > 0, "Expected JSON report file to be created"
    print("✓ Successful run test passed")

def test_verbose_mode():
    """Test verbose mode"""
    print("Testing verbose mode...")
    exit_code, stdout, stderr = run_command("python3 send_fox_report_gmail.py --no-email --verbose")
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
    # Check for DEBUG level logging or verbose-specific output
    combined_output = stdout + stderr
    assert "DEBUG:" in combined_output or "Arguments:" in combined_output, f"Expected verbose output, got: {combined_output[:200]}"
    print("✓ Verbose mode test passed")

def main():
    """Run all tests"""
    print("Running main orchestration tests...")
    print("=" * 50)

    try:
        test_help()
        test_mutually_exclusive_args()
        test_invalid_nights()
        test_config_not_found()
        test_successful_run()
        test_verbose_mode()

        print("=" * 50)
        print("✅ All tests passed!")
        return 0

    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
