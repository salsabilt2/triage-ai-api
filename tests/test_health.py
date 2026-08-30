"""Tests for the /health endpoint."""


def test_health_reports_ok(demo_client):
    response = demo_client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model"] == "gpt-5-nano"


def test_health_reports_demo_mode_when_no_key_is_set(demo_client):
    assert demo_client.get("/health").json()["demo_mode"] is True


def test_health_reports_live_mode_when_a_key_is_set(live_client):
    assert live_client.get("/health").json()["demo_mode"] is False
