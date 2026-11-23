"""Smoke tests for endpoints that do not need a database."""

from __future__ import annotations

import httpx
import pytest

from app.main import create_app


@pytest.fixture
def client() -> httpx.AsyncClient:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_liveness_does_not_touch_the_database(client: httpx.AsyncClient) -> None:
    async with client:
        response = await client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_meta_exposes_the_nine_steps(client: httpx.AsyncClient) -> None:
    async with client:
        response = await client.get("/api/meta")
    assert response.status_code == 200
    body = response.json()
    assert len(body["steps"]) == 9
    assert body["model_approval_after_step"] == 2
    # Bumped as each phase lands; the UI labels placeholder steps with it.
    assert body["build_phase"] >= 1
    assert body["risk_thresholds"]["high"] == 16


async def test_meta_never_returns_the_api_key(client: httpx.AsyncClient) -> None:
    async with client:
        response = await client.get("/api/meta")
    body = response.json()
    assert "llm_api_key" not in body
    assert set(body) >= {"llm_provider", "llm_configured"}
    # llm_configured is a boolean flag, not the secret itself.
    assert isinstance(body["llm_configured"], bool)


async def test_samples_endpoint_lists_every_bundled_scenario(
    client: httpx.AsyncClient,
) -> None:
    async with client:
        response = await client.get("/api/samples")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 6
    assert {s["doc_code"] for s in body} == {
        "MB-TRF-AD-007",
        "KRD-APP-SA-003",
        "OB-PLT-SA-001",
        "POS-ACQ-AD-012",
        "AI-ASST-AD-004",
        "YTR-TRD-AD-021",
    }
    # Every listed scenario must have its file, or the screen offers a
    # document that cannot be opened.
    assert all(s["available"] for s in body)
