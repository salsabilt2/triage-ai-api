"""FastAPI application: endpoints, error handling, and request logging."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import demo_mode
from app.ai_service import TriageService, TriageServiceError
from app.config import Settings, get_settings
from app.models import (
    BatchTriageRequest,
    BatchTriageResponse,
    ErrorResponse,
    HealthResponse,
    TriageRequest,
    TriageResponse,
    TriageResult,
    UsageInfo,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("triageai")

DESCRIPTION = """
Turns messy support tickets into structured, prioritised data.

Send raw ticket text and get back a summary, a category, an urgency level, and a suggested
first reply — validated against a strict schema, with token usage and estimated cost.

**No OpenAI key?** Leave `OPENAI_API_KEY` empty, or send `"demo": true`, and the API
returns realistic canned results so you can try everything.
"""

ERROR_RESPONSES = {
    429: {"model": ErrorResponse, "description": "AI service busy"},
    500: {"model": ErrorResponse, "description": "AI service misconfigured"},
    502: {"model": ErrorResponse, "description": "AI returned an unusable response"},
    503: {"model": ErrorResponse, "description": "AI service unavailable"},
    504: {"model": ErrorResponse, "description": "AI service timed out"},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the service once at startup so prompts and the HTTP client are reused."""
    settings = get_settings()
    app.state.service = TriageService(settings)
    logger.info(
        "TriageAI started | model=%s | prompt=v%s | demo_only=%s",
        settings.openai_model,
        settings.prompt_version,
        settings.demo_only,
    )
    yield


app = FastAPI(
    title="TriageAI",
    description=DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)

# The Streamlit UI runs on a different port, so it needs permission to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(TriageServiceError)
async def triage_error_handler(request: Request, exc: TriageServiceError) -> JSONResponse:
    """Turn our own errors into the right HTTP code with a message that is safe to show."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


def get_service(request: Request) -> TriageService:
    """The service built at startup, handed to endpoints by FastAPI."""
    return request.app.state.service


# Named dependencies keep the endpoint signatures short and readable.
ServiceDep = Annotated[TriageService, Depends(get_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _triage_one(
    ticket_text: str,
    use_demo: bool,
    service: TriageService,
    settings: Settings,
) -> TriageResponse:
    """Triage a single ticket through either the demo path or the real model.

    Shared by /triage and /triage/batch so the two endpoints cannot drift apart.
    """
    if use_demo or settings.demo_only:
        started = time.perf_counter()
        result: TriageResult = demo_mode.triage_demo(ticket_text)
        usage = UsageInfo(
            input_tokens=demo_mode.FAKE_INPUT_TOKENS,
            output_tokens=demo_mode.FAKE_OUTPUT_TOKENS,
            estimated_cost_usd=settings.estimate_cost(
                demo_mode.FAKE_INPUT_TOKENS, demo_mode.FAKE_OUTPUT_TOKENS
            ),
            elapsed_seconds=round(time.perf_counter() - started, 3),
            model=settings.openai_model,
            prompt_version=settings.prompt_version,
            demo_mode=True,
        )
    else:
        result, usage = service.triage(ticket_text)

    logger.info(
        "triage | demo=%s | category=%s | urgency=%s | tokens=%s+%s | cost=$%.6f | %.2fs",
        usage.demo_mode,
        result.category.value,
        result.urgency.value,
        usage.input_tokens,
        usage.output_tokens,
        usage.estimated_cost_usd,
        usage.elapsed_seconds,
    )
    return TriageResponse(result=result, usage=usage)


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health(settings: SettingsDep) -> HealthResponse:
    """Liveness check. Also reports whether the server has an API key configured."""
    return HealthResponse(
        status="ok",
        demo_mode=settings.demo_only,
        model=settings.openai_model,
        prompt_version=settings.prompt_version,
    )


@app.post("/triage", response_model=TriageResponse, responses=ERROR_RESPONSES, tags=["triage"])
def triage(
    payload: TriageRequest,
    service: ServiceDep,
    settings: SettingsDep,
) -> TriageResponse:
    """Triage one support ticket."""
    return _triage_one(payload.ticket_text, payload.demo, service, settings)


@app.post(
    "/triage/batch",
    response_model=BatchTriageResponse,
    responses=ERROR_RESPONSES,
    tags=["triage"],
)
def triage_batch(
    payload: BatchTriageRequest,
    service: ServiceDep,
    settings: SettingsDep,
) -> BatchTriageResponse:
    """Triage up to ten tickets in one call."""
    results = [_triage_one(text, payload.demo, service, settings) for text in payload.tickets]
    return BatchTriageResponse(results=results)
