"""
test_route_security.py
----------------------
Regression tests for API route security contracts.

These tests exist to prevent silent regressions in:
1. Unknown routes returning HTTP 404, not 200
2. The catch-all route (/{path_name:path} -> 200) must not be re-introduced

Verified bug fixed: 2026-10-03 Phase 1
Original bug: main.py had a catch-all api_route that returned HTTP 200 for
every unrecognized URL, hiding routing errors and removing 404 threat signal.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_unknown_get_route_returns_404_not_200():
    """
    Regression: the catch-all route used to return HTTP 200 for all unknown paths.
    This test ensures that is permanently gone.
    """
    response = client.get("/this/path/does/not/exist")
    assert response.status_code == 404, (
        f"Expected 404 for unknown route, got {response.status_code}. "
        "If this is 200, the catch-all route has been re-introduced — see main.py."
    )


def test_unknown_post_route_returns_404_not_200():
    """Catch-all covered GET, POST, PUT, DELETE, etc. — verify POST is also 404."""
    response = client.post("/nonexistent/endpoint", json={"key": "value"})
    assert response.status_code == 404, (
        f"Expected 404 for unknown POST route, got {response.status_code}."
    )


def test_404_response_body_does_not_expose_internals():
    """
    The 404 response must not contain stack traces, file system paths,
    route tables, or any internal detail — only a safe generic message.
    """
    response = client.get("/path/that/does/not/exist/at/all")
    assert response.status_code == 404
    body = response.json()
    body_str = str(body).lower()

    # Must not contain internal artifacts
    assert "traceback" not in body_str, "404 body must not expose a traceback"
    assert "c:\\" not in body_str, "404 body must not expose filesystem paths"
    assert "backend" not in body_str, "404 body must not expose internal module paths"

    # Must contain the standard error shape
    assert "error" in body or "message" in body, (
        "404 body should contain 'error' or 'message' key"
    )


def test_health_route_still_returns_200():
    """Sanity check: the real /health route must still work after the 404 handler change."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
