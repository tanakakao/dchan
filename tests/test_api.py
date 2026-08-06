"""Tests for the FastAPI optimal-design endpoints."""

from fastapi.testclient import TestClient

from application.main import app


client = TestClient(app)


def test_health() -> None:
    """Verify that the health endpoint reports a healthy service."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_candidate() -> None:
    """Verify that candidate points can be generated from numeric factors."""
    response = client.post(
        "/optimal-design/candidate",
        json={
            "factor_names": ["temperature", "time"],
            "x_upper": [100, 10],
            "x_lower": [0, 0],
            "x_step": [10, 1],
            "x_levels": [None, None],
            "opt_type": "D",
            "n_iter": 10,
            "n_samples": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["candidates"]) == 5
    assert set(body["candidates"][0]) == {"temperature", "time"}
    assert set(body["correlations"]) == {"temperature", "time"}


def test_rejects_mismatched_factor_lists() -> None:
    """Verify that inconsistent factor definitions receive a 422 response."""
    response = client.post(
        "/optimal-design/candidate",
        json={
            "factor_names": ["temperature", "time"],
            "x_upper": [100],
            "x_lower": [0, 0],
            "x_step": [10, 1],
            "x_levels": [None, None],
        },
    )

    assert response.status_code == 422
