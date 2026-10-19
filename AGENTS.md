# AGENTS.md

Context for AI coding agents working in this repository. Read this before changing anything.

## What this project is

TriageAI is a FastAPI service that turns one raw support ticket into structured data: a category, an urgency, a one-sentence summary and a suggested reply. A Streamlit page sits on top of it. It is a portfolio project written by Md Salsabil (GitHub: salsabilt2) and is meant to be read by recruiters, so clarity and honesty matter more than features.

It is not a customer-facing ticketing system. There is no login, no database and no stored tickets.

## Commands

Python is pinned to 3.12 (`.python-version`). Run everything from the repository root.

| Task | Command |
|---|---|
| Create the environment | `uv venv --python 3.12 && uv pip install -r requirements.txt` |
| Activate it | `source .venv/bin/activate` |
| Run the API | `uvicorn app.main:app --reload` (port 8000) |
| Run the page | `streamlit run ui/streamlit_app.py` (port 8501; needs the API running) |
| Run the tests | `pytest -q` (expect 24 passed) |
| Lint and format check | `ruff check . && ruff format --check .` |
| Format | `ruff format .` |

CI (`.github/workflows/ci.yml`) runs the linter and the tests on every push. Both must pass.

## How a request flows

1. `ui/streamlit_app.py` posts the ticket to `POST /triage` on the API. The page never imports `openai` and never sees the key.
2. `app/main.py` validates the body with `TriageRequest` (10 to 5,000 characters). Bad input gets a 422.
3. `_triage_one()` in `app/main.py` picks the path. It uses demo mode when the request sets `"demo": true` or when `Settings.demo_only` is true (no `OPENAI_API_KEY`). Otherwise it calls `TriageService.triage()`.
4. `app/ai_service.py` calls `client.responses.parse(..., text_format=TriageResult)`, so OpenAI enforces the schema. It retries once if the answer is a refusal or is cut short, then raises `TriageServiceError`.
5. `TriageServiceError(status_code, message)` is turned into JSON `{"detail": message}` by the handler in `app/main.py`.
6. The response carries a `result` (the four fields) and `usage` (tokens, estimated cost, time, model, prompt version, demo flag).

## File map

| Path | Responsibility |
|---|---|
| `app/config.py` | `Settings` (loaded from `.env`), `MODEL_PRICES`, `estimate_cost()`, `get_settings()` |
| `app/models.py` | All Pydantic models. `TriageResult` is the schema sent to OpenAI. `Category` and `Urgency` are enums |
| `app/ai_service.py` | `TriageService`: prompt loading, the OpenAI call, one retry, error mapping, cost |
| `app/demo_mode.py` | `triage_demo()`: four saved answers chosen by keyword score |
| `app/main.py` | Endpoints, CORS, logging, error handler, dependency wiring |
| `prompts/triage_v1.txt`, `triage_v2.txt` | Versioned system prompts. `PROMPT_VERSION` selects one. Default is 2 |
| `ui/streamlit_app.py` | The page: header, form, result card, history |
| `ui/examples.py` | `EXAMPLE_TICKETS`, the 19 dropdown examples |
| `ui/styles.css` | All page styling, injected by `streamlit_app.py` |
| `.streamlit/config.toml` | Streamlit theme colours and toolbar settings |
| `tests/conftest.py` | Fixtures that build a `TestClient` with a mocked OpenAI transport |
| `tests/test_*.py` | 24 tests across health, triage and error handling |
| `postman/` | Importable request collection |

## Rules to follow

- **Tests never touch the network or need a key.** The OpenAI SDK (v3) uses `httpx2`, not `httpx`, so `respx` cannot intercept it. Tests inject `httpx2.MockTransport` through `build_client()` in `tests/conftest.py`. Keep it that way.
- **Never commit `.env` or any key.** `.env` is in `.gitignore`. `.env.example` holds names only.
- **Do not leak configuration errors to callers.** A rejected API key returns a generic 500. The real cause goes to the log.
- **Settings in tests** are swapped with `app.dependency_overrides[get_settings]`, so tests ignore the developer's own `.env`.
- **Code style.** Ruff, 100-character lines, Python 3.12 syntax. Every non-empty module starts with a docstring. Match the existing comment density.
- **Commits.** Conventional style (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`), written as the repository owner. The owner asked that commits in this repository carry no `Co-Authored-By` line.
- **Do not state numbers you have not measured** in the README or in code comments.

## Things that surprise people

- `output_parsed` is `None` when the model refuses, so the code checks for it. That is the "unusable answer" case behind the 502.
- A live call to `gpt-5-nano` takes about 15 seconds and uses roughly 1,700 or more output tokens for a short answer, probably reasoning tokens. This has not been capped yet.
- The production client in `ai_service.py` uses the SDK's default retry settings. Tests set `max_retries=0`.
- Demo-mode answers are fixed, so a custom ticket can get an answer that does not describe it. The page tells the user.
- Streamlit caches imported modules. After editing `ui/examples.py`, restart `streamlit run`, because the page does not reload it by itself.
- `ui/styles.css` targets Streamlit 1.62 internals (`data-testid` attributes). A Streamlit upgrade can break those selectors. The result card uses plain `div`s on purpose, because Streamlit restyles `p` and `h2` inside markdown.
- Text from the API is escaped with `esc()` before it goes into HTML in `streamlit_app.py`. Keep doing that for anything that comes from a model or a user.
- `.venv` stores absolute paths, so moving the folder breaks it. Recreate it after a move.

## Common changes

- **Add a category:** add it to `Category` in `app/models.py`, describe it in `prompts/triage_v2.txt`, add a saved answer in `app/demo_mode.py`, add examples in `ui/examples.py`, and update the tests.
- **Add a prompt version:** create `prompts/triage_vN.txt` and set `PROMPT_VERSION=N`.
- **Change the model:** set `OPENAI_MODEL` and add its prices to `MODEL_PRICES` in `app/config.py`. Unknown models are priced at zero.
- **Add an example ticket:** add an entry to `EXAMPLE_TICKETS` in `ui/examples.py`, then restart Streamlit.

## Open work

1. Cap the model's output (reasoning effort and `max_output_tokens`) to cut cost and latency, then re-measure.
2. Compare prompt v1 and v2 on a labelled set of tickets and put the real result in the README.
3. Record the demo GIF and add it at the top of the README.
4. Not planned yet: authentication, storage, deployment, Docker.
