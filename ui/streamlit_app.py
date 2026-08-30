"""TriageAI user interface.

One page, one job. Note that this file never imports the OpenAI library and never sees an
API key — it only calls the FastAPI backend over HTTP. That separation is the whole point
of the project.
"""

import os

import requests
import streamlit as st

API_URL = os.getenv("TRIAGE_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 60
HISTORY_LENGTH = 5

URGENCY_COLOURS = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
CATEGORY_ICONS = {"Hardware": "🔧", "Software": "💻", "Billing": "💳", "Other": "📋"}

EXAMPLE_TICKETS = {
    "— Write my own —": "",
    "Industrial: conveyor motor overheating": (
        "Conveyor motor on line 3 is overheating and smells burnt. We shut the line down "
        "twenty minutes ago and production has stopped. This is the second time this month."
    ),
    "Billing: charged twice": (
        "Hi, I've just checked my statement and I've been charged twice for my monthly "
        "subscription. Same amount, same day. Can you sort this out please?"
    ),
    "Software: dashboard crashes": (
        "Ever since the update on Friday the reporting dashboard crashes as soon as I log "
        "in. I can still use the mobile app, so it isn't urgent, but it's slowing me down."
    ),
}

st.set_page_config(page_title="TriageAI", page_icon="🎫", layout="centered")


def check_backend() -> dict | None:
    """Ask the API whether it is up and whether it has a key configured."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def render_result(payload: dict) -> None:
    """Draw the results card for one triaged ticket."""
    result, usage = payload["result"], payload["usage"]
    category, urgency = result["category"], result["urgency"]

    left, right = st.columns(2)
    left.metric("Category", f"{CATEGORY_ICONS.get(category, '')} {category}")
    right.metric("Urgency", f"{URGENCY_COLOURS.get(urgency, '')} {urgency}")

    st.markdown("**Summary**")
    st.info(result["summary"])

    st.markdown("**Suggested reply**")
    st.success(result["suggested_reply"])

    tokens = usage["input_tokens"] + usage["output_tokens"]
    source = "demo response" if usage["demo_mode"] else usage["model"]
    st.caption(
        f"{tokens} tokens · ${usage['estimated_cost_usd']:.6f} estimated · "
        f"{usage['elapsed_seconds']:.2f}s · {source} · prompt v{usage['prompt_version']}"
    )


st.title("🎫 TriageAI")
st.caption("Paste any support ticket. Get instant triage.")

health = check_backend()
if health is None:
    st.error(
        f"Cannot reach the API at {API_URL}. Start it with:\n\n`uvicorn app.main:app --reload`"
    )
    st.stop()

if health["demo_mode"]:
    st.info("No API key configured, so every request returns a realistic demo response.")

if "history" not in st.session_state:
    st.session_state.history = []

choice = st.selectbox("Example tickets", list(EXAMPLE_TICKETS))
ticket_text = st.text_area("Ticket text", value=EXAMPLE_TICKETS[choice], height=170)

action, toggle = st.columns([1, 2])
submitted = action.button("🔍 Triage Ticket", type="primary", use_container_width=True)
force_demo = toggle.checkbox(
    "Demo mode (no key needed)",
    value=health["demo_mode"],
    disabled=health["demo_mode"],
    help="Returns a saved example response instead of calling the AI.",
)

if submitted:
    if len(ticket_text.strip()) < 10:
        st.warning("Please enter at least 10 characters.")
    else:
        with st.spinner("Triaging…"):
            try:
                response = requests.post(
                    f"{API_URL}/triage",
                    json={"ticket_text": ticket_text.strip(), "demo": force_demo},
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as exc:
                st.error(f"Could not reach the API: {exc}")
            else:
                if response.status_code == 200:
                    payload = response.json()
                    render_result(payload)
                    st.session_state.history.insert(
                        0,
                        {
                            "Ticket": ticket_text.strip()[:60] + "…",
                            "Category": payload["result"]["category"],
                            "Urgency": payload["result"]["urgency"],
                            "Cost ($)": f"{payload['usage']['estimated_cost_usd']:.6f}",
                            "Time (s)": f"{payload['usage']['elapsed_seconds']:.2f}",
                        },
                    )
                    st.session_state.history = st.session_state.history[:HISTORY_LENGTH]
                else:
                    detail = response.json().get("detail", "Unknown error")
                    st.error(f"{response.status_code}: {detail}")

if st.session_state.history:
    st.divider()
    st.markdown(f"📜 **Session history** (last {HISTORY_LENGTH})")
    st.dataframe(st.session_state.history, use_container_width=True, hide_index=True)
