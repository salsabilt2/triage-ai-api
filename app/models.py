"""Pydantic models: the contract for what goes in, what comes out, and what the AI may say."""

from enum import Enum

from pydantic import BaseModel, Field

MAX_TICKET_LENGTH = 5000
MAX_BATCH_SIZE = 10


class Category(str, Enum):
    """The only categories the AI is allowed to choose from."""

    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    BILLING = "Billing"
    OTHER = "Other"


class Urgency(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class TriageResult(BaseModel):
    """The structured answer we require from the model.

    This class is sent to OpenAI as a JSON schema, so the model cannot return free text,
    invent a category, or omit a field. It is also what we validate against afterwards.
    """

    summary: str = Field(description="One sentence describing the problem, max 25 words.")
    category: Category = Field(description="Which type of issue this is.")
    urgency: Urgency = Field(description="How quickly a human needs to act.")
    suggested_reply: str = Field(description="A polite first reply to the customer, 2-4 sentences.")


class UsageInfo(BaseModel):
    """What the request cost and how it was served."""

    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    elapsed_seconds: float
    model: str
    prompt_version: int
    demo_mode: bool


class TriageRequest(BaseModel):
    """A single incoming ticket.

    FastAPI validates this before our code runs, so empty or oversized text is rejected
    with a clear 422 automatically.
    """

    ticket_text: str = Field(
        min_length=10,
        max_length=MAX_TICKET_LENGTH,
        description="The raw support ticket text.",
    )
    demo: bool = Field(
        default=False,
        description="Force a canned response instead of calling the AI.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ticket_text": (
                        "Conveyor motor on line 3 is overheating and smells burnt. "
                        "Production has stopped."
                    ),
                    "demo": True,
                }
            ]
        }
    }


class BatchTriageRequest(BaseModel):
    """Several tickets in one call."""

    tickets: list[str] = Field(min_length=1, max_length=MAX_BATCH_SIZE)
    demo: bool = False


class TriageResponse(BaseModel):
    """What the API returns: the AI's answer plus what it cost to produce."""

    result: TriageResult
    usage: UsageInfo


class BatchTriageResponse(BaseModel):
    results: list[TriageResponse]


class HealthResponse(BaseModel):
    status: str
    demo_mode: bool
    model: str
    prompt_version: int


class ErrorResponse(BaseModel):
    """Every error the API returns uses this shape, so clients can rely on it."""

    detail: str
