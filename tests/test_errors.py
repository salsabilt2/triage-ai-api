"""Tests for every failure path the API is expected to handle.

Each one proves the caller gets the right HTTP code and a message that is safe to show.
"""

import httpx2
import pytest

from tests.conftest import SAMPLE_TICKET, openai_response_body

LONG_TICKET = "a" * 5001


@pytest.mark.parametrize(
    ("ticket_text", "reason"),
    [
        ("", "empty input"),
        ("help", "shorter than the minimum"),
        (LONG_TICKET, "longer than the maximum"),
    ],
)
def test_invalid_input_is_rejected_with_422(demo_client, ticket_text, reason):
    response = demo_client.post("/triage", json={"ticket_text": ticket_text})

    assert response.status_code == 422, reason


def test_rate_limit_becomes_429(make_live_client):
    def handler(request):
        return httpx2.Response(429, json={"error": {"message": "rate limit"}})

    response = make_live_client(handler).post("/triage", json={"ticket_text": SAMPLE_TICKET})

    assert response.status_code == 429
    assert "busy" in response.json()["detail"].lower()


def test_timeout_becomes_504(make_live_client):
    def handler(request):
        raise httpx2.TimeoutException("too slow", request=request)

    response = make_live_client(handler).post("/triage", json={"ticket_text": SAMPLE_TICKET})

    assert response.status_code == 504


def test_connection_failure_becomes_503(make_live_client):
    def handler(request):
        raise httpx2.ConnectError("no route to host", request=request)

    response = make_live_client(handler).post("/triage", json={"ticket_text": SAMPLE_TICKET})

    assert response.status_code == 503


def test_bad_api_key_becomes_500_and_never_leaks_the_reason(make_live_client):
    def handler(request):
        return httpx2.Response(401, json={"error": {"message": "Incorrect API key provided"}})

    response = make_live_client(handler).post("/triage", json={"ticket_text": SAMPLE_TICKET})

    assert response.status_code == 500
    detail = response.json()["detail"].lower()
    # The caller is told the server is misconfigured, not what the key looks like.
    assert "key" not in detail
    assert "sk-" not in detail


def test_unusable_ai_output_becomes_502_after_a_retry(make_live_client):
    """The model returns a refusal twice, so we give up with a clean 502."""
    calls = []

    def handler(request):
        calls.append(request)
        body = openai_response_body({})
        body["output"] = [
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "refusal", "refusal": "I cannot help with that."}],
            }
        ]
        return httpx2.Response(200, json=body)

    response = make_live_client(handler).post("/triage", json={"ticket_text": SAMPLE_TICKET})

    assert response.status_code == 502
    assert len(calls) == 2, "the service should try twice before giving up"


def test_a_retry_recovers_when_the_second_attempt_is_valid(make_live_client):
    """First call is a refusal, second is fine — the caller should never see the wobble."""
    from tests.conftest import VALID_AI_ANSWER

    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            body = openai_response_body({})
            body["output"] = [
                {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "refusal", "refusal": "I cannot help with that."}],
                }
            ]
            return httpx2.Response(200, json=body)
        return httpx2.Response(200, json=openai_response_body(VALID_AI_ANSWER))

    response = make_live_client(handler).post("/triage", json={"ticket_text": SAMPLE_TICKET})

    assert response.status_code == 200
    assert len(calls) == 2
    assert response.json()["result"]["category"] == "Hardware"
