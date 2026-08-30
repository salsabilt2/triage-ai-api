"""The OpenAI call: prompt loading, structured output, one retry, and cost accounting.

The guiding idea is that the language model is an unreliable external service. OpenAI
enforces our JSON schema on its side, but we still check what comes back and retry once
before giving up, because a model can refuse, run out of output tokens, or stop early.
"""

import logging
import time

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    LengthFinishReasonError,
    OpenAI,
    RateLimitError,
)

from app.config import Settings
from app.models import TriageResult, UsageInfo

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2


class TriageServiceError(Exception):
    """Something went wrong that the caller needs to know about.

    `status_code` is the HTTP code the API should return, and `message` is safe to show a
    user — it never contains keys, URLs, or stack details.
    """

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class TriageService:
    """Wraps the OpenAI client. Built once at startup and reused for every request."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.prompt = self._load_prompt()
        self.client = (
            OpenAI(api_key=settings.openai_api_key, timeout=settings.request_timeout)
            if not settings.demo_only
            else None
        )

    def _load_prompt(self) -> str:
        """Read the versioned prompt file once, at startup, not on every request."""
        path = self.settings.prompt_path
        if not path.is_file():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    def triage(self, ticket_text: str) -> tuple[TriageResult, UsageInfo]:
        """Send one ticket to the model and return a validated result plus usage figures."""
        if self.client is None:
            raise TriageServiceError(500, "The AI service is not configured.")

        started = time.perf_counter()
        last_problem = ""

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self.client.responses.parse(
                    model=self.settings.openai_model,
                    instructions=self.prompt,
                    input=ticket_text,
                    text_format=TriageResult,
                )
            except RateLimitError as exc:
                raise TriageServiceError(
                    429, "The AI service is busy right now. Please try again shortly."
                ) from exc
            except APITimeoutError as exc:
                raise TriageServiceError(
                    504, "The AI service took too long to respond. Please try again."
                ) from exc
            except AuthenticationError as exc:
                # The real cause goes to the log only. Telling a caller that the server's
                # key is wrong leaks a configuration detail they cannot act on.
                logger.error("OpenAI rejected the API key — check OPENAI_API_KEY in .env")
                raise TriageServiceError(500, "The AI service is misconfigured.") from exc
            except APIConnectionError as exc:
                raise TriageServiceError(503, "The AI service is unavailable.") from exc
            except LengthFinishReasonError as exc:
                # The model ran out of room before finishing its JSON.
                last_problem = "response was cut short"
                logger.warning("Attempt %s/%s: %s", attempt, MAX_ATTEMPTS, last_problem)
                if attempt == MAX_ATTEMPTS:
                    raise TriageServiceError(502, "The AI returned an unusable response.") from exc
                continue

            result = response.output_parsed
            if result is None:
                # A refusal, or output that did not survive validation.
                last_problem = getattr(response, "refusal", None) or "no valid result returned"
                logger.warning("Attempt %s/%s: %s", attempt, MAX_ATTEMPTS, last_problem)
                if attempt == MAX_ATTEMPTS:
                    raise TriageServiceError(502, "The AI returned an unusable response.")
                continue

            usage = self._build_usage(response, started)
            return result, usage

        # Unreachable: the loop either returns or raises. Kept so the type checker agrees.
        raise TriageServiceError(502, "The AI returned an unusable response.")

    def _build_usage(self, response: object, started: float) -> UsageInfo:
        """Turn the API's token counts into our own usage record, including cost."""
        raw = getattr(response, "usage", None)
        input_tokens = getattr(raw, "input_tokens", 0) or 0
        output_tokens = getattr(raw, "output_tokens", 0) or 0

        return UsageInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=self.settings.estimate_cost(input_tokens, output_tokens),
            elapsed_seconds=round(time.perf_counter() - started, 3),
            model=self.settings.openai_model,
            prompt_version=self.settings.prompt_version,
            demo_mode=False,
        )
