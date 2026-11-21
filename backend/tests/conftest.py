from __future__ import annotations

import os

import pytest

# Tests must never reach a real database; endpoints that need one are not
# exercised here (they are covered by the end-to-end replay test in phase 5).
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)
os.environ.setdefault("APP_NAME", "Tehdit Modelleme Platformu")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
