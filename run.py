#!/usr/bin/env python3
"""
Simple run script for the LLM Tool Orchestrator
This is a convenient wrapper around main.py
"""
import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run main
if __name__ == '__main__':
    from main import cli
    cli()
