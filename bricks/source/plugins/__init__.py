"""Explicitly import each plugin so its @REGISTRY.register decorator fires."""
from __future__ import annotations

from . import email, folder, s3  # noqa: F401
