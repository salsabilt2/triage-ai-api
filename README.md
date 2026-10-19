# TriageAI

A small API that reads a raw support ticket and returns a category, an urgency, a one-sentence summary and a draft reply.

[![CI](https://github.com/salsabilt2/triage-ai-api/actions/workflows/ci.yml/badge.svg)](https://github.com/salsabilt2/triage-ai-api/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

<!-- Add the demo GIF here once it is recorded: ![TriageAI demo](docs/demo.gif) -->

## What it does

You paste a ticket the way a customer wrote it. TriageAI sends it to an OpenAI model and returns four fields.

| Field | Values |
|---|---|
| Category | Hardware, Software, Billing or Other |
| Urgency | Low, Medium or High |
| Summary | One sentence |
| Suggested reply | A short, polite first response |

Every response also reports the tokens used, the estimated cost and the time taken.

The person I had in mind is a support agent who sorts incoming tickets all day, so the page is written for them. The example tickets lean toward industrial faults, such as a conveyor motor overheating or a hydraulic press losing pressure, with billing and software cases next to them.

This is a portfolio project. It has no login, it does not store tickets, and it is not deployed anywhere.

## Try it without an API key

The app works with no OpenAI account. When no key is configured, every request returns a saved answer instead of calling the model.

```bash
git clone https://github.com/salsabilt2/triage-ai-api.git
cd triage-ai-api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is now running at <http://localhost:8000>, and the interactive docs are at <http://localhost:8000/docs>. For the web page, open a second terminal in the same folder and run:

```bash
source .venv/bin/activate
streamlit run ui/streamlit_app.py
```

The page opens at <http://localhost:8501>.

Demo mode matches your ticket against keywords and returns one of four saved answers, one per category. A ticket you write yourself gets the answer that fits its category best, which may not describe your ticket. The page says so under every demo result. For an answer written for your ticket, use the real model.

## Run it with the real model

Copy the example settings file, then put your OpenAI key in it.

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY=` to your key, restart the API, and untick "Demo mode" on the page. The `.env` file is listed in `.gitignore`, so the key stays on your machine.

| Setting | Default | What it controls |
|---|---|---|
| `OPENAI_API_KEY` | empty | Leave empty for demo mode |
| `OPENAI_MODEL` | `gpt-5-nano` | Which model answers |
| `PROMPT_VERSION` | `2` | Which file in `prompts/` is used |
| `REQUEST_TIMEOUT` | `30` | Seconds to wait for OpenAI |

## How it works

```
 Streamlit page ──HTTP──►  FastAPI backend  ──HTTPS──►  OpenAI
 Postman / curl ◄──JSON──  (validates, parses)  ◄─JSON──  model
 Swagger /docs
```

The page never talks to OpenAI. It only calls my API, and the API holds the key. A request goes through these steps:

1. Pydantic checks the ticket: 10 to 5,000 characters, otherwise the API returns a 422.
2. The API loads the prompt from `prompts/` (read once at startup).
3. It asks the model for an answer in a fixed schema.
4. It checks what came back, and retries once if the answer is unusable.
5. It logs the tokens and estimated cost, then returns the result.

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Reports status, model, prompt version and whether a key is set |
| `/triage` | POST | Triage one ticket |
| `/triage/batch` | POST | Triage up to 10 tickets in one call |
| `/docs` | GET | Swagger UI |

A real request and response from the live model:

```json
{
  "ticket_text": "The dashboard has been crashing every time I try to export a report since yesterday."
}
```

```json
{
  "result": {
    "summary": "Dashboard crashes when exporting a report since yesterday.",
    "category": "Software",
    "urgency": "Medium",
    "suggested_reply": "Thanks for reporting. I'm escalating this to our software team to investigate the dashboard export crash and collect any relevant logs. We'll provide an update within the next 24 hours. In the meantime, does the crash occur for all reports or only a specific report?"
  },
  "usage": {
    "input_tokens": 788,
    "output_tokens": 1734,
    "estimated_cost_usd": 0.000733,
    "elapsed_seconds": 15.477,
    "model": "gpt-5-nano",
    "prompt_version": 2,
    "demo_mode": false
  }
}
```

Add `"demo": true` to a request to get a saved answer even when a key is configured.

Errors always come back as `{"detail": "..."}` with a message that is safe to show a user.

| Code | When |
|---|---|
| 422 | The ticket is empty, shorter than 10 characters or longer than 5,000 |
| 429 | OpenAI is rate limiting the request |
| 500 | The server's API key is missing or rejected. The real reason goes to the server log only |
| 502 | The model returned an unusable answer twice |
| 503 | OpenAI could not be reached |
| 504 | OpenAI took too long |

A [Postman collection](postman/TriageAI.postman_collection.json) with these requests is in the repo.

## Keeping the model's output reliable

I treat the model as an outside service that can fail, because it can.

The expected answer is a Pydantic model, `TriageResult`, passed to OpenAI as the output schema. Category and urgency are enums, so the model cannot return a fifth category.

The model can still refuse, or run out of output tokens halfway through. Both cases are caught. An unusable answer is retried once, and if the second attempt fails too, the caller gets a 502 and never a half-parsed result.

The code is in [`app/ai_service.py`](app/ai_service.py). Rate-limit and timeout errors from OpenAI become a 429 and a 504, and the app adds no retry of its own for them.

## Prompts

Prompts are plain text files in [`prompts/`](prompts/), so a change to the wording shows up in git like any other change. `PROMPT_VERSION` picks which one runs.

`triage_v1.txt` is a short instruction: read the ticket and return the four fields.

`triage_v2.txt` is the default. It adds:

- a definition of each category;
- a rule that urgency follows impact and not the customer's tone;
- a one-sentence limit on the summary;
- limits on the reply: no promised refunds or visit times, and at most one question;
- one worked example.

I wrote v2 from how I expected the model to go wrong. I have not yet run the two versions side by side on a set of tickets, so I can't say how much better v2 is. That comparison is the next piece of prompt work.

## Cost and speed

`gpt-5-nano` costs $0.05 per million input tokens and $0.40 per million output tokens (OpenAI's published price in August 2026). The prices live in one table in [`app/config.py`](app/config.py).

In my two live test runs, one ticket cost between $0.0007 and $0.0008 and took 14 to 15 seconds. That is roughly 1,300 tickets per dollar.

The output side is larger than I expected. The first run used 788 input tokens and 1,734 output tokens for an answer of a few sentences, so most of the output looks like the model's own reasoning. I have not capped it yet. Doing that should cut both the cost and the wait, and it is first on my list.

Demo mode reports fixed token counts, so its cost figure is only a placeholder.

## Tests

```bash
pytest -v
ruff check . && ruff format --check .
```

There are 24 tests, and none of them calls OpenAI or needs a key. The OpenAI SDK sends requests through `httpx2`, so the tests give its client a mock transport that answers locally. The real SDK, schema parsing and error handling all run against a fake server.

The tests cover the health endpoint, demo mode, a live-style call, the retry that recovers, the retry that gives up, input validation, the rate-limit, timeout, connection and bad-key errors, and the cost arithmetic. GitHub Actions runs the tests and the linter on every push.

## Project layout

```
app/
  config.py       settings, loaded from .env, plus the price table
  models.py       request, response and model-output schemas
  ai_service.py   the OpenAI call, retry and cost calculation
  demo_mode.py    saved answers for demo mode
  main.py         endpoints, error handling and logging
prompts/          versioned prompt files
ui/
  streamlit_app.py  the page
  examples.py       the 19 example tickets
  styles.css        the page styling
.streamlit/         Streamlit theme settings
tests/            24 tests, no network access
postman/          importable API collection
AGENTS.md         notes for AI coding agents working on this repo
```

## Limitations

- A live call takes about 15 seconds, and the page handles one ticket at a time.
- Nothing is stored. The page keeps the last five results for the current session only.
- There is no login or rate limiting, so it is not safe to expose publicly as it stands.
- `/triage/batch` works through its tickets one after another. If one fails, the whole call fails, and the page does not use this endpoint.
- Demo-mode answers do not describe a ticket you write yourself.

## What I would build next

1. Cap the model's output to cut the cost and the wait.
2. Build a labelled set of about 50 tickets and score each prompt version automatically, so "v2 is better" becomes a number.
3. Store triaged tickets in a database behind login, so results can be reviewed.
4. Containerise and deploy it, with a spend alert based on the cost figures it already logs.

## License

MIT. See [LICENSE](LICENSE).
