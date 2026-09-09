"""Vercel serverless entrypoint. The package lives under backend/, which is not on sys.path
in the lambda, so put it there before importing the app Vercel will serve."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from setubiz.api.main import app  # noqa: E402

__all__ = ["app"]
