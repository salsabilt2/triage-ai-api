"""Canned responses so the API works with no OpenAI key.

Why this exists: anyone can clone the repository and see the app working immediately.
The answers are hand-written, picked by keyword, and returned after a short pause so the
UI spinner behaves the same as it does against the real model.
"""

import time

from app.models import Category, TriageResult, Urgency

# A small artificial delay so demo mode feels like a real network call.
FAKE_LATENCY_SECONDS = 0.4

# Rough token counts, so the cost display in the UI still has something to show.
FAKE_INPUT_TOKENS = 380
FAKE_OUTPUT_TOKENS = 95

_RESPONSES: list[tuple[tuple[str, ...], TriageResult]] = [
    (
        ("motor", "overheat", "conveyor", "burnt", "vibration", "bearing", "machine"),
        TriageResult(
            summary="Conveyor line 3 motor is overheating and production has stopped.",
            category=Category.HARDWARE,
            urgency=Urgency.HIGH,
            suggested_reply=(
                "Thank you for reporting this. An overheating motor with a burning smell is a "
                "safety risk, so please keep line 3 powered down. I am escalating this to our "
                "on-site maintenance team now and will confirm an engineer's arrival time within "
                "the hour."
            ),
        ),
    ),
    (
        ("invoice", "billing", "charge", "refund", "payment", "subscription", "price"),
        TriageResult(
            summary="Customer was charged twice for the same monthly subscription.",
            category=Category.BILLING,
            urgency=Urgency.MEDIUM,
            suggested_reply=(
                "Thank you for flagging this, and sorry for the trouble. I can see a duplicate "
                "charge on your account and have passed it to our billing team for a refund. "
                "Refunds usually clear within three to five working days, and I will email you "
                "once it is processed."
            ),
        ),
    ),
    (
        ("login", "password", "crash", "error", "bug", "app", "software", "update", "screen"),
        TriageResult(
            summary="Dashboard crashes on load after the latest software update.",
            category=Category.SOFTWARE,
            urgency=Urgency.MEDIUM,
            suggested_reply=(
                "Thanks for letting us know. A crash straight after an update usually points to a "
                "cached settings file, so could you try signing out and back in once? I have also "
                "logged this with our engineering team and will update you if it turns out to be a "
                "wider issue."
            ),
        ),
    ),
]

_FALLBACK = TriageResult(
    summary="General support request with no clear hardware, software, or billing cause.",
    category=Category.OTHER,
    urgency=Urgency.LOW,
    suggested_reply=(
        "Thank you for getting in touch. I have logged your request and a member of the support "
        "team will review it shortly. If anything changes in the meantime, just reply to this "
        "message and it will reach the same person."
    ),
)


def triage_demo(ticket_text: str) -> TriageResult:
    """Return a realistic canned result, chosen by the first keyword group that matches."""
    time.sleep(FAKE_LATENCY_SECONDS)

    lowered = ticket_text.lower()
    for keywords, result in _RESPONSES:
        if any(word in lowered for word in keywords):
            return result
    return _FALLBACK
