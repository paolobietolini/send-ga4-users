"""Browser session management using Playwright for GA4 user bootstrapping."""

import asyncio
import re
import time
from dataclasses import dataclass

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from config import SimulationConfig
from measurement_protocol import GA4User


@dataclass
class SessionData:
    """Data extracted from a browser session."""

    client_id: str
    session_id: int
    page_title: str
    page_location: str


class BrowserSessionManager:
    """Manages browser sessions for bootstrapping GA4 users."""

    def __init__(self, config: SimulationConfig, measurement_id: str):
        self.config = config
        self.measurement_id = measurement_id
        self._playwright = None
        self._browser: Browser | None = None

    async def __aenter__(self) -> "BrowserSessionManager":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, *args) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def create_session(self, timeout_ms: int = 30000) -> SessionData:
        """
        Create a new browser session, visit the target URL,
        and extract the GA4 client_id from cookies.
        """
        if not self._browser:
            raise RuntimeError("Browser not initialized. Use async context manager.")

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=self._get_random_user_agent(),
        )

        try:
            page = await context.new_page()

            # Navigate to target URL
            await page.goto(self.config.target_url, wait_until="networkidle")

            # Wait a bit for GA4 to initialize
            await asyncio.sleep(2)

            # Extract session data
            session_data = await self._extract_session_data(context, page)

            return session_data

        finally:
            await context.close()

    async def create_session_with_engagement(
        self, engagement_time_ms: int = 5000
    ) -> SessionData:
        """
        Create a session and simulate user engagement.
        This helps ensure the user appears in GA4 reports.
        """
        if not self._browser:
            raise RuntimeError("Browser not initialized. Use async context manager.")

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=self._get_random_user_agent(),
        )

        try:
            page = await context.new_page()

            # Navigate to target URL
            await page.goto(self.config.target_url, wait_until="networkidle")

            # Simulate engagement (scroll, wait)
            await self._simulate_engagement(page, engagement_time_ms)

            # Extract session data
            session_data = await self._extract_session_data(context, page)

            return session_data

        finally:
            await context.close()

    async def _extract_session_data(
        self, context: BrowserContext, page: Page
    ) -> SessionData:
        """Extract GA4 client_id and session_id from browser cookies."""
        cookies = await context.cookies()

        client_id = None
        session_id = None

        # Look for _ga cookie (contains client_id)
        # Format: GA1.1.XXXXXXXXXX.XXXXXXXXXX or GA1.2.XXXXXXXXXX.XXXXXXXXXX
        for cookie in cookies:
            if cookie["name"] == "_ga":
                match = re.search(r"GA\d+\.\d+\.(\d+\.\d+)", cookie["value"])
                if match:
                    client_id = match.group(1)

            # Look for _ga_<container_id> cookie (contains session_id)
            # The measurement_id without "G-" prefix
            container_id = self.measurement_id.replace("G-", "")
            if cookie["name"] == f"_ga_{container_id}":
                # Format: GS1.1.XXXXXXXXXX.N.C.XXXXXXXXXX.XX.X.X
                match = re.search(r"GS\d+\.\d+\.(\d+)", cookie["value"])
                if match:
                    session_id = int(match.group(1))

        # Fallback: generate client_id if not found
        if not client_id:
            client_id = f"{int(time.time())}.{int(time.time() * 1000) % 1000000000}"

        # Fallback: use current timestamp for session_id
        if not session_id:
            session_id = int(time.time())

        return SessionData(
            client_id=client_id,
            session_id=session_id,
            page_title=await page.title(),
            page_location=page.url,
        )

    async def _simulate_engagement(self, page: Page, duration_ms: int) -> None:
        """Simulate user engagement on the page."""
        start_time = time.time()
        target_duration = duration_ms / 1000

        while (time.time() - start_time) < target_duration:
            # Random scroll
            scroll_y = 100 + int((time.time() * 1000) % 300)
            await page.evaluate(f"window.scrollBy(0, {scroll_y})")
            await asyncio.sleep(0.5 + (time.time() % 1))

            # Move mouse randomly
            x = 100 + int((time.time() * 1000) % 800)
            y = 100 + int((time.time() * 1000) % 400)
            await page.mouse.move(x, y)

    def _get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        # Use time-based selection for variety
        return user_agents[int(time.time() * 1000) % len(user_agents)]

    def session_to_user(self, session_data: SessionData) -> GA4User:
        """Convert session data to a GA4User object."""
        return GA4User(
            client_id=session_data.client_id,
            session_id=session_data.session_id,
        )
