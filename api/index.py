"""Vercel entrypoint for the CloudPulse API.

Vercel's Python runtime looks for an ASGI application named `app` in `api/index.py`.
The service itself stays in `backend/app/main.py` so the container build (Dockerfile) and the
serverless build share a single source of truth.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
