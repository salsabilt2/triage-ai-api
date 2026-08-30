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
        (
            "motor",
            "overheat",
            "conveyor",
            "burnt",
            "burning",
            "smoke",
            "vibration",
            "bearing",
            "machine",
            "belt",
            "gearbox",
            "spindle",
            "fan",
            "cable",
            "sensor",
            "hardware",
            "device",
            "equipment",
            "broken",
            "leak",
            "noise",
        ),
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
        (
            "hydraulic",
            "press",
            "pressure",
            "pump",
            "valve",
            "seal",
            "cylinder",
            "compressor",
            "hose",
        ),
        TriageResult(
            summary="Hydraulic press is losing pressure mid-cycle and output has halved.",
            category=Category.HARDWARE,
            urgency=Urgency.MEDIUM,
            suggested_reply=(
                "Thank you for the detailed report. Pressure loss that worsens over several days "
                "usually points to a seal or valve issue, so I am passing this to our hydraulics "
                "team for review today. Could you confirm the pressure reading at the start and "
                "end of a cycle? That will help the engineer arrive with the right parts."
            ),
        ),
    ),
    (
        (
            "invoice",
            "billing",
            "billed",
            "charge",
            "charged",
            "refund",
            "payment",
            "subscription",
            "price",
            "quote",
            "receipt",
            "card",
            "renewal",
        ),
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
        (
            "login",
            "log in",
            "password",
            "crash",
            "crashes",
            "error",
            "bug",
            "app",
            "software",
            "update",
            "screen",
            "dashboard",
            "browser",
            "firmware",
            "portal",
            "account",
            "sync",
            "export",
            "report",
        ),
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
    """Return a realistic canned result for the ticket.

    Every keyword group is scored and the best match wins, rather than the first one that
    happens to match. That keeps a billing question that mentions a machine in Billing.
    """
    time.sleep(FAKE_LATENCY_SECONDS)

    lowered = ticket_text.lower()
    best_score = 0
    best_result = _FALLBACK

    for keywords, result in _RESPONSES:
        score = sum(word in lowered for word in keywords)
        if score > best_score:
            best_score, best_result = score, result

    return best_result
