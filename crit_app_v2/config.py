"""Configuration owned by the next-generation application."""

import os

DEBUG = os.getenv("DASH_DEBUG", "true").lower() in {"1", "true", "yes", "on"}
