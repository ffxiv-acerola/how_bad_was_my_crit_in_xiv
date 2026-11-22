"""Configuration owned by the next-generation application."""

import os
from pathlib import Path

DEBUG = os.getenv("DASH_DEBUG", "true").lower() in {"1", "true", "yes", "on"}
DB_URI = Path(
    os.getenv("DB_URI", Path(__file__).resolve().parents[1] / "data/reports.db")
)
