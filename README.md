# 🎫 TriageAI — Smart Support Ticket API

**Turns messy support tickets into structured, prioritised data — automatically.**

[![CI](https://github.com/salsabilt2/triage-ai-api/actions/workflows/ci.yml/badge.svg)](https://github.com/salsabilt2/triage-ai-api/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

<!-- Replace this line with your demo GIF: ![TriageAI demo](docs/demo.gif) -->

> **Try it with no OpenAI key.** Clone, install, run. With no key configured the API returns
> realistic saved responses, so the whole app works out of the box.

---

## What it does

- **Reads** a raw support ticket — the kind a person actually types, punctuation and all.
- **Returns** a one-line summary, a category (Hardware / Software / Billing / Other), an
  urgency level (Low / Medium / High), and a suggested first reply to the customer.
- **Reports** how many tokens the request used and what it cost, on every single response.

Built around industrial fault reports — a conveyor motor overheating, a hydraulic press
losing pressure — but it works on any support inbox.

---

## Architecture

```
┌──────────────┐        ┌──────────────────────────────┐        ┌────────────┐
│    Client    │  HTTP  │       FastAPI Backend        │ HTTPS  │   OpenAI   │
│              │ ─────► │                              │ ─────► │            │
│ Streamlit UI │        │ 1. Validate input (Pydantic) │        │  LLM model │
│ Postman/curl │ ◄───── │ 2. Load versioned prompt     │ ◄───── │            │
│ Swagger /docs│  JSON  │ 3. Call OpenAI (JSON schema) │  JSON  │            │
└──────────────┘        │ 4. Validate output + retry   │        └────────────┘
                        │ 5. Log tokens + cost         │
                        └──────────────────────────────┘
```

**The rule this project is built on:** the UI never talks to OpenAI. It only talks to *this*
API. The API key lives on the server and never reaches the browser.

---

## Quickstart

```bash
git clone https://github.com/salsabilt2/triage-ai-api.git
cd triage-ai-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://localhost:8000/docs> and try it. That is everything — **no API key needed**.

To use the real model, copy `.env.example` to `.env` and add your key:

```bash
cp .env.example .env   # then set OPENAI_API_KEY=sk-...
```

To run the web UI, in a second terminal:

```bash
streamlit run ui/streamlit_app.py
```

---

## API reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check, plus whether a key is configured |
| `/triage` | POST | One ticket in → structured triage out |
| `/triage/batch` | POST | Up to 10 tickets in one call |
| `/docs` | GET | Interactive Swagger UI |

**Request**

```json
{
  "ticket_text": "Conveyor motor on line 3 is overheating and smells burnt. Production has stopped.",
  "demo": false
}
```

**Response**

```json
{
  "result": {
    "summary": "Conveyor line 3 motor is overheating and production has stopped.",
    "category": "Hardware",
    "urgency": "High",
    "suggested_reply": "Thank you for reporting this. An overheating motor with a burning smell is a safety risk, so please keep line 3 powered down. I am escalating this to our on-site maintenance team now and will confirm an engineer's arrival time within the hour."
  },
  "usage": {
    "input_tokens": 412,
    "output_tokens": 88,
    "estimated_cost_usd": 5.5e-05,
    "elapsed_seconds": 1.83,
    "model": "gpt-5-nano",
    "prompt_version": 2,
    "demo_mode": false
  }
}
```

**Errors.** Every failure returns `{"detail": "..."}` with a message that is safe to show a
user. Nothing about the server's configuration leaks to the caller.

| Situation | Code |
|---|---|
| Ticket empty, too short, or over 5,000 characters | `422` |
| OpenAI rate limit reached | `429` |
| Server's API key is missing or rejected | `500` |
| Model returned unusable output twice | `502` |
| Cannot reach OpenAI | `503` |
| OpenAI took too long | `504` |

A [Postman collection](postman/TriageAI.postman_collection.json) with all of these is in the repo.

---

## How the AI output is kept trustworthy

The language model is treated as an unreliable external service, because that is what it is.

1. **The schema is enforced, not requested.** `TriageResult` is a Pydantic model sent to
   OpenAI as a JSON schema, so the model physically cannot return free text, invent a
   fifth category, or drop a field.
2. **The answer is still checked.** A model can refuse, or run out of output tokens
   mid-JSON. Both are caught.
3. **One retry, then a clean failure.** If the second attempt is also unusable, the caller
   gets a `502` — never a half-parsed object or a crash.

See [`app/ai_service.py`](app/ai_service.py).

---

## Prompt design notes

Prompts live in [`prompts/`](prompts/) as versioned files, not buried in the code. Switch
between them with `PROMPT_VERSION` in `.env`.

**v1** was the obvious first attempt: "read the ticket, give a summary, category, urgency
and reply." It produced reasonable text but three problems showed up quickly:

- **Urgency tracked tone, not impact.** A politely-worded "the press has stopped" scored
  lower than an angry message about a cosmetic bug.
- **Summaries restated the ticket** instead of compressing it.
- **Replies over-promised** — inventing refund timelines and engineer visit times that
  nobody had agreed to.

**v2** fixes each one directly:

- Urgency is defined by **consequence**, with an explicit rule: *judge the impact, not the
  customer's tone*. High means stopped production, a safety risk, data loss, or money
  leaving an account.
- The summary has a hard limit (one sentence, 25 words) and must name the system and the
  symptom.
- The reply section forbids promises the business has not made, and asks exactly one
  question when the ticket is thin on detail.
- One worked example is included, because a single concrete example constrains tone more
  reliably than another paragraph of instructions.

**Next step:** these are reasoned design changes validated by hand on the sample tickets.
The honest next move is a small labelled set of ~50 tickets and an automated score per
prompt version, so "v2 is better" becomes a number rather than an opinion.

---

## Testing

```bash
pytest -v
ruff check .
```

24 tests, and **not one of them touches the network or needs an API key**. The OpenAI SDK
communicates over `httpx2`, so the tests hand it a `MockTransport` that answers locally.
That means the real SDK, the real schema parsing, and the real error handling all run —
just against a fake server.

Covered: the health endpoint, demo mode, live parsing, the retry that recovers, the retry
that gives up, every input-validation rule, and all five network failure modes. GitHub
Actions runs the whole suite plus the linter on every push.

---

## Cost awareness

`gpt-5-nano` is priced at $0.05 per million input tokens and $0.40 per million output
tokens (August 2026). A typical triage call is roughly 400 input and 90 output tokens —
about **$0.00006 per ticket**, or under a dollar for 15,000 tickets.

Every response carries its own token count and cost estimate, and every request writes one
log line with the same figures. Prices live in one table in
[`app/config.py`](app/config.py), so updating them is a one-line change.

---

## What I'd build next

- **Persistence and auth** — store triaged tickets in Postgres behind API-key auth, so
  results can be reviewed and the prompt versions compared on real historical data.
- **A real evaluation harness** — a labelled ticket set scored automatically, turning
  prompt changes into measured improvements instead of judgement calls.
- **Deployment** — containerise and deploy behind a rate limiter, with the cost figures
  already being logged wired into a dashboard and a spend alert.

---

## Project layout

```
app/
  config.py       settings and model prices, all in one place
  models.py       the request, response, and AI-output contracts
  ai_service.py   OpenAI call, retry, cost accounting
  demo_mode.py    canned answers, so the app runs with no key
  main.py         endpoints, error handlers, logging
prompts/          versioned prompt files (v1, v2)
ui/               Streamlit front end
tests/            24 tests, no network access
postman/          importable API collection
```

## License

MIT
