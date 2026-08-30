"""Application settings, loaded once from the environment or a .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Price per 1,000,000 tokens in USD, taken from OpenAI's pricing page (August 2026).
# Used only to show an estimate — it is not billing data.
MODEL_PRICES: dict[str, tuple[float, float]] = {
    # model: (input price, output price)
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o-mini": (0.15, 0.60),
}


class Settings(BaseSettings):
    """Everything configurable lives here, so nothing is hardcoded elsewhere."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-5-nano"
    prompt_version: int = 2
    request_timeout: float = 30.0

    @property
    def demo_only(self) -> bool:
        """True when no API key is configured, so the app falls back to canned answers.

        This is what lets someone clone the repository and run it without an OpenAI account.
        """
        return not self.openai_api_key.strip()

    @property
    def prompt_path(self) -> Path:
        return PROMPTS_DIR / f"triage_v{self.prompt_version}.txt"

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimated USD cost of one request. Unknown models are priced at zero."""
        input_price, output_price = MODEL_PRICES.get(self.openai_model, (0.0, 0.0))
        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
        return round(cost, 6)


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is read once, not on every request."""
    return Settings()
