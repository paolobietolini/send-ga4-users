"""Configuration management for GA4 User Simulator."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
load_dotenv(Path(__file__).parent / ".env")


@dataclass
class GA4Config:
    """GA4 Measurement Protocol configuration."""

    measurement_id: str
    mp_secret: str

    @property
    def mp_endpoint(self) -> str:
        """GA4 Measurement Protocol endpoint."""
        return (
            f"https://www.google-analytics.com/mp/collect"
            f"?measurement_id={self.measurement_id}"
            f"&api_secret={self.mp_secret}"
        )

    @property
    def debug_endpoint(self) -> str:
        """GA4 Measurement Protocol debug endpoint."""
        return (
            f"https://www.google-analytics.com/debug/mp/collect"
            f"?measurement_id={self.measurement_id}"
            f"&api_secret={self.mp_secret}"
        )


@dataclass
class SimulationConfig:
    """Simulation parameters configuration."""

    target_url: str
    max_concurrent_users: int
    max_daily_users: int
    min_session_duration_ms: int
    max_session_duration_ms: int
    min_pages_per_session: int
    max_pages_per_session: int


@dataclass
class Config:
    """Main configuration container."""

    ga4: GA4Config
    simulation: SimulationConfig


def load_config() -> Config:
    """Load configuration from environment variables."""

    ga4 = GA4Config(
        measurement_id=os.environ["GA4_MEASUREMENT_ID"],
        mp_secret=os.environ["GA4_MP_SECRET"],
    )

    simulation = SimulationConfig(
        target_url=os.environ.get("TARGET_URL", "https://paolobietolini.me"),
        max_concurrent_users=int(os.environ.get("MAX_CONCURRENT_USERS", 50)),
        max_daily_users=int(os.environ.get("MAX_DAILY_USERS", 1000)),
        min_session_duration_ms=int(os.environ.get("MIN_SESSION_DURATION_MS", 5000)),
        max_session_duration_ms=int(os.environ.get("MAX_SESSION_DURATION_MS", 120000)),
        min_pages_per_session=int(os.environ.get("MIN_PAGES_PER_SESSION", 1)),
        max_pages_per_session=int(os.environ.get("MAX_PAGES_PER_SESSION", 5)),
    )

    return Config(ga4=ga4, simulation=simulation)
