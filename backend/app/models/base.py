"""Declarative base and shared column helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for every ORM model."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
