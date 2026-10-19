"""TriageAI user interface.

One page, one job. Note that this file never imports the OpenAI library and never sees an
API key — it only calls the FastAPI backend over HTTP. That separation is the whole point
of the project.
"""

import html
import os
from pathlib import Path

import requests
import streamlit as st
from examples import EXAMPLE_TICKETS

API_URL = os.getenv("TRIAGE_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 60
HISTORY_LENGTH = 5
MIN_TICKET_LENGTH = 10

LOGO_MARK = (
    '<svg viewBox="0 0 28 28" aria-hidden="true">'
    '<rect width="28" height="28" rx="8" fill="#0e6b66"/>'
    '<rect x="6" y="7" width="16" height="3" rx="1.5" fill="#fff"/>'
    '<rect x="6" y="12.5" width="11" height="3" rx="1.5" fill="#fff" fill-opacity=".75"/>'
    '<rect x="6" y="18" width="6" height="3" rx="1.5" fill="#fff" fill-opacity=".5"/>'
    "</svg>"
)

st.set_page_config(page_title="TriageAI", page_icon=":material/support_agent:", layout="wide")
st.markdown(
    f"<style>{(Path(__file__).parent / 'styles.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)


def esc(text: str) -> str:
    """Escape text for HTML. Dollar signs are escaped too, so Markdown never reads them as maths."""
    return html.escape(text).replace("$", "&#36;")


def check_backend() -> dict | None:
    """Ask the API whether it is up and whether it has a key configured."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def header_html(health: dict | None) -> str:
    """Top bar: wordmark on the left, a short how-to in the middle, API status on the right."""
    if health is None:
        status = '<div class="status offline"><i></i>API offline</div>'
    elif health["demo_mode"]:
        status = '<div class="status demo"><i></i>Demo mode · no API key</div>'
    else:
        status = f'<div class="status"><i></i>Live · {esc(health["model"])}</div>'

    return (
        '<header class="topbar">'
        f'<div class="brand">{LOGO_MARK}<span>TriageAI</span></div>'
        '<ol class="guide">'
        '<li><b>1</b><span>Paste a ticket<span class="long"> or pick an example</span></span></li>'
        "<li><b>2</b><span>Press Triage Ticket</span></li>"
        "<li><b>3</b><span>Get a category, urgency, summary"
        '<span class="long"> and draft reply</span></span></li>'
        "</ol>"
        f"{status}"
        "</header>"
    )


def empty_html() -> str:
    """What the results card shows before the first ticket: it explains what you will get."""
    rows = [
        ("Category", "What kind of problem it is: hardware, software, billing or other."),
        ("Urgency", "How soon someone needs to act: low, medium or high."),
        ("Summary", "The problem in one sentence, so you do not have to reread the ticket."),
        ("Suggested reply", "A polite first response you can edit and send."),
    ]
    items = "".join(f"<div><dt>{name}</dt><dd>{text}</dd></div>" for name, text in rows)
    return (
        '<section class="card empty">'
        '<div class="card-title" role="heading" aria-level="2">Your triage will appear here</div>'
        '<div class="lead">Each ticket comes back with four things:</div>'
        f"<dl>{items}</dl>"
        "</section>"
    )


def loading_html() -> str:
    return (
        '<section class="card skeleton" aria-busy="true">'
        '<div class="bar short"></div><div class="bar short"></div>'
        '<div class="wait">Triaging your ticket. Real AI calls can take up to 15 seconds.</div>'
        '<div class="bar"></div><div class="bar"></div><div class="bar tall"></div>'
        "</section>"
    )


def problem_html(title: str, detail: str) -> str:
    return (
        '<section class="card problem">'
        f'<div class="card-title" role="heading" aria-level="2">{esc(title)}</div>'
        f'<div class="detail">{detail}</div>'
        "</section>"
    )


def result_html(payload: dict) -> str:
    """The results card for one triaged ticket."""
    result, usage = payload["result"], payload["usage"]
    category, urgency = result["category"], result["urgency"]

    tokens = usage["input_tokens"] + usage["output_tokens"]
    source = "demo response" if usage["demo_mode"] else usage["model"]
    note = (
        '<div class="note">Demo response: a saved answer, not written for your ticket. '
        "Turn demo mode off to get a real one.</div>"
        if usage["demo_mode"]
        else ""
    )
    return (
        '<article class="card enter">'
        '<div class="fields">'
        '<div class="field"><span class="field-label">Category</span>'
        f'<span class="chip">{esc(category)}</span></div>'
        f'<div class="field"><span class="field-label">Urgency</span>'
        f'<span class="pill {esc(urgency.lower())}"><i></i>{esc(urgency)}</span></div>'
        "</div>"
        '<div class="label">Summary</div>'
        f'<div class="summary">{esc(result["summary"])}</div>'
        '<div class="label">Suggested reply</div>'
        f'<div class="reply">{esc(result["suggested_reply"])}</div>'
        f"{note}"
        f'<div class="meta">{tokens} tokens · ${usage["estimated_cost_usd"]:.6f} estimated · '
        f"{usage['elapsed_seconds']:.2f}s · {esc(source)} · prompt v{usage['prompt_version']}</div>"
        "</article>"
    ).replace("$", "&#36;")


def load_example() -> None:
    """Copy the chosen example into the ticket box.

    Anything that is not a listed example (the dropdown also accepts typed text) is treated
    as the visitor's own ticket. Clearing the dropdown leaves the ticket box untouched.
    """
    choice = st.session_state.example_choice
    if choice:
        st.session_state.ticket_text = EXAMPLE_TICKETS.get(choice, choice)


def triage(ticket: str, demo: bool) -> tuple[dict | None, str | None]:
    """Call the API. Returns (payload, None) on success or (None, problem html) on failure."""
    try:
        response = requests.post(
            f"{API_URL}/triage",
            json={"ticket_text": ticket, "demo": demo},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return None, problem_html(
            "Could not reach the API", f"Check that it is running at {esc(API_URL)}."
        )
    if response.status_code == 200:
        return response.json(), None
    detail = response.json().get("detail", "Unknown error")
    if not isinstance(detail, str):
        detail = "The ticket was not accepted. Check its length and try again."
    return None, problem_html(f"Something went wrong ({response.status_code})", esc(detail))


health = check_backend()
st.markdown(header_html(health), unsafe_allow_html=True)

if health is None:
    st.markdown(
        problem_html(
            "The API is not running",
            f"Start it in another terminal with <code>uvicorn app.main:app --reload</code>, "
            f"then refresh this page. Looking for it at {esc(API_URL)}.",
        ),
        unsafe_allow_html=True,
    )
    st.stop()

st.session_state.setdefault("history", [])
st.session_state.setdefault("card", empty_html())

form, output = st.columns([5, 6], gap="large")

with form:
    ticket_text = st.text_area(
        "Support ticket",
        key="ticket_text",
        height=200,
        placeholder="Paste or type a support ticket here...",
    )
    st.selectbox(
        "Or try an example",
        list(EXAMPLE_TICKETS),
        index=None,
        placeholder="Choose an example ticket...",
        key="example_choice",
        accept_new_options=True,
        on_change=load_example,
    )
    action, toggle = st.columns([1, 1.4], vertical_alignment="center")
    submitted = action.button("Triage Ticket", type="primary", use_container_width=True)
    force_demo = toggle.checkbox(
        "Demo mode (no key needed)",
        value=health["demo_mode"],
        disabled=health["demo_mode"],
        help="Returns a saved example response instead of calling the AI.",
    )

with output:
    slot = st.empty()

if submitted:
    ticket = ticket_text.strip()
    if len(ticket) < MIN_TICKET_LENGTH:
        st.session_state.card = problem_html(
            "That ticket is too short", f"Enter at least {MIN_TICKET_LENGTH} characters."
        )
    else:
        slot.markdown(loading_html(), unsafe_allow_html=True)
        payload, problem = triage(ticket, force_demo)
        if payload is None:
            st.session_state.card = problem
        else:
            st.session_state.card = result_html(payload)
            st.session_state.history.insert(
                0,
                {
                    "Ticket": ticket[:60] + ("…" if len(ticket) > 60 else ""),
                    "Category": payload["result"]["category"],
                    "Urgency": payload["result"]["urgency"],
                    "Cost ($)": f"{payload['usage']['estimated_cost_usd']:.6f}",
                    "Time (s)": f"{payload['usage']['elapsed_seconds']:.2f}",
                },
            )
            st.session_state.history = st.session_state.history[:HISTORY_LENGTH]

slot.markdown(st.session_state.card, unsafe_allow_html=True)

if st.session_state.history:
    st.markdown(
        f'<div class="history-title" role="heading" aria-level="2">'
        f"Recent triages (last {HISTORY_LENGTH})</div>",
        unsafe_allow_html=True,
    )
    st.dataframe(st.session_state.history, use_container_width=True, hide_index=True)
