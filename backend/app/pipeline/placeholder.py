"""Placeholder content for the steps that are not implemented yet.

All nine steps are implemented as of phase 4, so this module is empty. It
stays in place as the hook for any future step that needs a placeholder:
anything listed in ``PLACEHOLDER_STEPS`` publishes ``placeholder: true`` and
the UI labels it as sample data.
"""

from __future__ import annotations

PLACEHOLDER_STEPS = frozenset()

COUNTERS: dict[int, dict[str, int]] = {}

MESSAGES: dict[int, list[str]] = {}
