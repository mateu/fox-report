#!/usr/bin/env python3
"""
Fox Report CLI Entry Point

This is a convenience wrapper that allows running the CLI from the project root
while maintaining the new hierarchical structure.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the CLI
from cli.send_report import main

if __name__ == "__main__":
    main()
