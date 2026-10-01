#!/usr/bin/env python3
"""Project execution script for AI-Based Predictive System Health Monitoring.

Provides the root-level CLI entry point to launch the application.
Ensures the repository root is properly registered on the Python search path.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is available on sys.path regardless of execution context
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
