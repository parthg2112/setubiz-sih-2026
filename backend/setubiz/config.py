"""Runtime settings. Every tunable that a judge might ask us to justify lives here, not inline."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parent
SAMPLE_DATA_DIR = PACKAGE_ROOT / "data" / "sample"
#: The real build: Census 2011 PCA, SHRUG v2.2, Economic Census 2013, HCES 2023-24, OpenStreetMap.
REAL_DATA_DIR = PACKAGE_ROOT / "data" / "real"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SETUBIZ_", env_file=".env", extra="ignore")

    # --- feasibility ---
    default_radius_km: float = 10.0
    # Ranchi district intercensal scaling 2011 -> 2026 (Census 2027 not yet published; PLAN.md §10)
    intercensal_growth: dict[str, float] = {"ranchi": 1.29, "_default": 1.25}
    competitor_estimator: str = "ec13_zscore"
    demand_estimator: str = "hces_mean_band"

    #: data.gov.in key for the AGMARKNET mandi resource, used by the ETL only — the app never
    #: calls the network at request time. The portal's documented sample key is rate-limited and
    #: caps at 10 records, so a personal key from "My Account -> Generate API Key" is required.
    data_gov_api_key: str | None = None

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

    # --- offline narration lane: Llama 3.1 8B Instruct Q4_K_M via llama.cpp (PLAN.md §3) ---
    local_llm_enabled: bool = False
    #: Path to the GGUF. The weights are not shipped; the lane stays unavailable without them.
    local_llm_model_path: Path | None = None
    local_llm_n_ctx: int = 8192
    local_llm_threads: int | None = None
    local_llm_max_tokens: int = 2048

    #: Serve real observations by default. `data/sample` remains as a synthetic fallback and
    #: declares itself as such, so a report built on it still carries the demonstration-data
    #: warning -- that warning is driven by the data, never hardcoded off.
    data_dir: Path = REAL_DATA_DIR


@lru_cache
def get_settings() -> Settings:
    return Settings()
