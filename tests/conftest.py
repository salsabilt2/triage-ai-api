"""Shared test fixtures.

No test ever reaches the network. The OpenAI SDK talks over httpx2, so we hand its client
a `MockTransport` that answers every request locally. That means the tests still exercise
the real SDK, the real schema parsing, and our real error handling — just without a key.
"""

import json

import httpx2
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

from app.ai_service import TriageService
from app.config import Settings, get_settings
from app.main import app

VALID_AI_ANSWER = {
    "summary": "Line 3 conveyor motor is overheating and production has stopped.",
    "category": "Hardware",
    "urgency": "High",
    "suggested_reply": "Thank you for reporting this. Please keep line 3 powered down.",
}

SAMPLE_TICKET = "Conveyor motor on line 3 is overheating and smells burnt. Production has stopped."


def openai_response_body(answer: dict, input_tokens: int = 412, output_tokens: int = 88) -> dict:
    """Build the JSON body the Responses API would return for a successful call."""
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 0,
        "model": "gpt-5-nano",
        "status": "completed",
        "parallel_tool_calls": False,
        "tool_choice": "auto",
        "tools": [],
        "output": [
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "annotations": [], "text": json.dumps(answer)}],
            }
        ],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }


@pytest.fixture
def demo_settings() -> Settings:
    """Settings with no API key, so the app runs entirely in demo mode."""
    return Settings(openai_api_key="", openai_model="gpt-5-nano", prompt_version=2)


@pytest.fixture
def live_settings() -> Settings:
    """Settings with a fake key, so the app takes the real code path to a mocked API."""
    return Settings(openai_api_key="sk-test-not-a-real-key", openai_model="gpt-5-nano")


def build_client(settings: Settings, handler) -> TestClient:
    """A TestClient whose service calls `handler` instead of OpenAI.

    `handler` receives the outgoing request and returns an httpx2.Response, or raises to
    simulate a network failure. The settings dependency is overridden too, so the app sees
    the test's configuration rather than whatever is in the developer's .env file.
    """
    service = TriageService(settings)
    if not settings.demo_only:
        service.client = OpenAI(
            api_key=settings.openai_api_key,
            max_retries=0,  # tests should fail fast, not sit through SDK backoff
            http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        )

    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    client.app.state.service = service
    return client


@pytest.fixture
def demo_client(demo_settings):
    """A client with no API key at all."""

    def handler(request):
        raise AssertionError("Demo mode must not make network calls")

    yield build_client(demo_settings, handler)
    app.dependency_overrides.clear()


@pytest.fixture
def live_client(live_settings):
    """A client that reaches a mocked OpenAI returning a valid answer."""

    def handler(request):
        return httpx2.Response(200, json=openai_response_body(VALID_AI_ANSWER))

    yield build_client(live_settings, handler)
    app.dependency_overrides.clear()


@pytest.fixture
def make_live_client(live_settings):
    """Factory for tests that need their own failing or unusual OpenAI handler."""

    def factory(handler) -> TestClient:
        return build_client(live_settings, handler)

    yield factory
    app.dependency_overrides.clear()
