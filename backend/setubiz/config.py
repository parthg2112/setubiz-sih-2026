"""Runtime settings. Every tunable that a judge might ask us to justify lives here, not inline."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parent
SAMPLE_DATA_DIR = PACKAGE_ROOT / "data" / "sample"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SETUBIZ_", env_file=".env", extra="ignore")

    # --- feasibility ---
    default_radius_km: float = 10.0
    # Ranchi district intercensal scaling 2011 -> 2026 (Census 2027 not yet published; PLAN.md §10)
    intercensal_growth: dict[str, float] = {"ranchi": 1.29, "_default": 1.25}
    competitor_estimator: str = "ec13_zscore"
    demand_estimator: str = "hces_mean_band"

    # --- decision layer ---
    dscr_threshold: Decimal = Decimal("1.5")
    stress_factors: tuple[Decimal, ...] = (Decimal("0.85"), Decimal("0.70"))
    #: A recommended loan must also survive the first stress scenario at this DSCR.
    stress_dscr_floor: Decimal = Decimal("1.0")
    enforce_stress_floor: bool = True
    recommended_loan_step: Decimal = Decimal("1000")

    # --- language layer ---
    llm_enabled: bool = False
    llm_model: str = "claude-opus-5"
    llm_effort: str = "low"
    llm_max_attempts: int = 3
    anthropic_api_key: str | None = None

    data_dir: Path = SAMPLE_DATA_DIR


@lru_cache
def get_settings() -> Settings:
    return Settings()
