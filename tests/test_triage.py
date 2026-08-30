"""Tests for the /triage and /triage/batch endpoints."""

from app.config import MODEL_PRICES, Settings
from app.models import Category, Urgency
from tests.conftest import SAMPLE_TICKET


def test_demo_mode_returns_a_complete_result(demo_client):
    response = demo_client.post("/triage", json={"ticket_text": SAMPLE_TICKET})

    assert response.status_code == 200
    body = response.json()
    assert set(body["result"]) == {"summary", "category", "urgency", "suggested_reply"}
    assert body["usage"]["demo_mode"] is True
    assert body["result"]["summary"]


def test_category_and_urgency_are_always_valid_values(demo_client):
    tickets = [
        SAMPLE_TICKET,
        "I was charged twice for my subscription this month, please refund.",
        "The dashboard crashes every time I log in after the latest update.",
        "Could you send me the user manual for the packaging line?",
    ]
    for ticket in tickets:
        body = demo_client.post("/triage", json={"ticket_text": ticket}).json()

        assert body["result"]["category"] in {c.value for c in Category}
        assert body["result"]["urgency"] in {u.value for u in Urgency}


def test_live_call_parses_the_models_structured_answer(live_client):
    response = live_client.post("/triage", json={"ticket_text": SAMPLE_TICKET})

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["category"] == "Hardware"
    assert body["result"]["urgency"] == "High"
    assert body["usage"]["demo_mode"] is False
    assert body["usage"]["input_tokens"] == 412
    assert body["usage"]["output_tokens"] == 88


def test_demo_flag_skips_the_ai_even_when_a_key_is_configured(live_client):
    body = live_client.post("/triage", json={"ticket_text": SAMPLE_TICKET, "demo": True}).json()

    assert body["usage"]["demo_mode"] is True


def test_batch_returns_one_result_per_ticket(demo_client):
    response = demo_client.post(
        "/triage/batch",
        json={"tickets": [SAMPLE_TICKET, "I was charged twice on my invoice."]},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[1]["result"]["category"] == "Billing"


def test_cost_estimate_matches_the_published_price():
    settings = Settings(openai_api_key="", openai_model="gpt-5-nano")
    input_price, output_price = MODEL_PRICES["gpt-5-nano"]

    expected = (1_000_000 * input_price + 1_000_000 * output_price) / 1_000_000

    assert settings.estimate_cost(1_000_000, 1_000_000) == round(expected, 6)
    assert settings.estimate_cost(0, 0) == 0.0


def test_unknown_model_is_priced_at_zero_rather_than_crashing():
    settings = Settings(openai_api_key="", openai_model="some-future-model")

    assert settings.estimate_cost(1000, 1000) == 0.0
