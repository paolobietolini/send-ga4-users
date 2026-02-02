"""User simulation orchestrator for GA4."""

import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum

from faker import Faker

from browser_session import BrowserSessionManager
from config import Config
from measurement_protocol import GA4User, MeasurementProtocolClient


class SimulationMode(Enum):
    """Simulation mode."""

    BROWSER_ONLY = "browser"  # Full browser simulation (slowest, most realistic)
    MP_ONLY = "mp"  # Measurement Protocol only (fastest, partial data)
    HYBRID = "hybrid"  # Browser bootstrap + MP events (recommended)


@dataclass
class SimulationStats:
    """Statistics for the simulation run."""

    users_created: int = 0
    events_sent: int = 0
    errors: int = 0
    start_time: float = 0
    end_time: float = 0

    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time

    @property
    def users_per_second(self) -> float:
        if self.duration_seconds > 0:
            return self.users_created / self.duration_seconds
        return 0


class UserSimulator:
    """Orchestrates GA4 user simulation."""

    def __init__(self, config: Config, mode: SimulationMode = SimulationMode.HYBRID):
        self.config = config
        self.mode = mode
        self.fake = Faker()
        self._stats = SimulationStats()
        self._semaphore: asyncio.Semaphore | None = None

    async def simulate_users(
        self,
        num_users: int,
        debug: bool = False,
        progress_callback: callable = None,
    ) -> SimulationStats:
        """
        Simulate the specified number of users.

        Args:
            num_users: Number of users to simulate
            debug: Use GA4 debug endpoint for validation
            progress_callback: Optional callback(current, total) for progress updates
        """
        # Respect daily limit
        num_users = min(num_users, self.config.simulation.max_daily_users)

        self._stats = SimulationStats(start_time=time.time())

        # Cap concurrency to avoid overwhelming DNS/network
        max_concurrent = self.config.simulation.max_concurrent_users
        if self.mode in (SimulationMode.BROWSER_ONLY, SimulationMode.HYBRID):
            max_concurrent = min(max_concurrent, 10)  # Cap browser concurrency
        else:
            max_concurrent = min(max_concurrent, 20)  # Cap MP concurrency

        self._semaphore = asyncio.Semaphore(max_concurrent)

        if self.mode == SimulationMode.MP_ONLY:
            await self._simulate_mp_only(num_users, debug, progress_callback)
        elif self.mode == SimulationMode.BROWSER_ONLY:
            await self._simulate_browser_only(num_users, progress_callback)
        else:
            await self._simulate_hybrid(num_users, debug, progress_callback)

        self._stats.end_time = time.time()
        return self._stats

    async def _simulate_mp_only(
        self,
        num_users: int,
        debug: bool,
        progress_callback: callable,
    ) -> None:
        """Simulate users using Measurement Protocol only."""
        async with MeasurementProtocolClient(self.config.ga4, debug=debug) as mp_client:
            # Process in batches for better memory management
            batch_size = 100
            for batch_start in range(0, num_users, batch_size):
                batch_end = min(batch_start + batch_size, num_users)
                tasks = [
                    self._create_mp_user(mp_client, i, num_users, progress_callback)
                    for i in range(batch_start, batch_end)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                # Log any exceptions that weren't handled
                for r in results:
                    if isinstance(r, Exception):
                        pass  # Already counted in _create_mp_user

    async def _create_mp_user(
        self,
        mp_client: MeasurementProtocolClient,
        index: int,
        total: int,
        progress_callback: callable,
    ) -> None:
        """Create a single user via Measurement Protocol."""
        async with self._semaphore:
            try:
                # Generate unique client_id
                client_id = f"{int(time.time())}{index}.{random.randint(1000000000, 9999999999)}"
                user = GA4User.create_new(client_id)

                # Send session_start
                await mp_client.send_session_start(
                    user,
                    page_location=self.config.simulation.target_url,
                    page_title="Home",
                )

                # Send first_visit for new users
                await mp_client.send_first_visit(user)

                # Send page_view
                engagement_time = random.randint(
                    self.config.simulation.min_session_duration_ms,
                    self.config.simulation.max_session_duration_ms,
                )
                await mp_client.send_page_view(
                    user,
                    page_location=self.config.simulation.target_url,
                    page_title="Home",
                    engagement_time_msec=engagement_time,
                )

                # Send user_engagement
                await mp_client.send_user_engagement(
                    user,
                    engagement_time_msec=engagement_time,
                    page_location=self.config.simulation.target_url,
                )

                self._stats.users_created += 1
                self._stats.events_sent += 4

                if progress_callback:
                    progress_callback(self._stats.users_created, total)

            except Exception as e:
                self._stats.errors += 1
                print(f"Error creating MP user: {e}")

    async def _simulate_browser_only(
        self,
        num_users: int,
        progress_callback: callable,
    ) -> None:
        """Simulate users using browser only (most realistic)."""
        async with BrowserSessionManager(
            self.config.simulation, self.config.ga4.measurement_id
        ) as browser_mgr:
            # Process in batches to avoid overwhelming the site
            batch_size = 10
            for batch_start in range(0, num_users, batch_size):
                batch_end = min(batch_start + batch_size, num_users)
                tasks = [
                    self._create_browser_user(browser_mgr, i, num_users, progress_callback)
                    for i in range(batch_start, batch_end)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                # Log any exceptions that weren't handled
                for r in results:
                    if isinstance(r, Exception):
                        pass  # Already counted in _create_browser_user

    async def _create_browser_user(
        self,
        browser_mgr: BrowserSessionManager,
        index: int,
        total: int,
        progress_callback: callable,
    ) -> None:
        """Create a single user via browser session."""
        async with self._semaphore:
            try:
                engagement_time = random.randint(
                    self.config.simulation.min_session_duration_ms,
                    self.config.simulation.max_session_duration_ms,
                )

                await browser_mgr.create_session_with_engagement(engagement_time)

                self._stats.users_created += 1
                # Browser sessions trigger events automatically via gtag
                self._stats.events_sent += 3  # session_start, first_visit, page_view

                if progress_callback:
                    progress_callback(self._stats.users_created, total)

            except Exception as e:
                self._stats.errors += 1
                print(f"Error creating browser user: {e}")

    async def _simulate_hybrid(
        self,
        num_users: int,
        debug: bool,
        progress_callback: callable,
    ) -> None:
        """Simulate users using hybrid approach (browser bootstrap + MP events)."""
        async with BrowserSessionManager(
            self.config.simulation, self.config.ga4.measurement_id
        ) as browser_mgr:
            async with MeasurementProtocolClient(
                self.config.ga4, debug=debug
            ) as mp_client:
                # Process in batches to avoid overwhelming the site
                batch_size = 10
                for batch_start in range(0, num_users, batch_size):
                    batch_end = min(batch_start + batch_size, num_users)
                    tasks = [
                        self._create_hybrid_user(
                            browser_mgr, mp_client, i, num_users, progress_callback
                        )
                        for i in range(batch_start, batch_end)
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    # Log any exceptions that weren't handled
                    for r in results:
                        if isinstance(r, Exception):
                            pass  # Already counted in _create_hybrid_user

    async def _create_hybrid_user(
        self,
        browser_mgr: BrowserSessionManager,
        mp_client: MeasurementProtocolClient,
        index: int,
        total: int,
        progress_callback: callable,
    ) -> None:
        """Create a single user via hybrid approach."""
        async with self._semaphore:
            try:
                # Step 1: Bootstrap session via browser (creates real user)
                session_data = await browser_mgr.create_session()
                user = browser_mgr.session_to_user(session_data)

                self._stats.events_sent += 3  # Browser triggers session_start, first_visit, page_view

                # Step 2: Send additional events via MP (fast)
                num_additional_pages = random.randint(
                    self.config.simulation.min_pages_per_session - 1,
                    self.config.simulation.max_pages_per_session - 1,
                )

                for _ in range(num_additional_pages):
                    engagement_time = random.randint(
                        self.config.simulation.min_session_duration_ms // 2,
                        self.config.simulation.max_session_duration_ms // 2,
                    )

                    # Simulate navigating to a different page
                    page_paths = ["/about", "/contact", "/blog", "/projects", "/resume"]
                    page_path = random.choice(page_paths)
                    page_url = f"{self.config.simulation.target_url}{page_path}"

                    await mp_client.send_page_view(
                        user,
                        page_location=page_url,
                        page_title=page_path.strip("/").title() or "Home",
                        page_referrer=session_data.page_location,
                        engagement_time_msec=engagement_time,
                    )
                    self._stats.events_sent += 1

                    # Small delay between events
                    await asyncio.sleep(random.uniform(0.1, 0.5))

                # Final user_engagement event
                total_engagement = random.randint(
                    self.config.simulation.min_session_duration_ms,
                    self.config.simulation.max_session_duration_ms,
                )
                await mp_client.send_user_engagement(
                    user,
                    engagement_time_msec=total_engagement,
                    page_location=self.config.simulation.target_url,
                )
                self._stats.events_sent += 1

                self._stats.users_created += 1

                if progress_callback:
                    progress_callback(self._stats.users_created, total)

            except Exception as e:
                self._stats.errors += 1
                print(f"Error creating hybrid user: {e}")


async def run_simulation(
    config: Config,
    num_users: int,
    mode: SimulationMode = SimulationMode.HYBRID,
    debug: bool = False,
) -> SimulationStats:
    """
    Run a user simulation.

    Args:
        config: Configuration object
        num_users: Number of users to simulate
        mode: Simulation mode (browser, mp, or hybrid)
        debug: Use GA4 debug endpoint

    Returns:
        SimulationStats with results
    """
    simulator = UserSimulator(config, mode)

    def progress(current, total):
        print(f"\rProgress: {current}/{total} users ({current * 100 // total}%)", end="")

    stats = await simulator.simulate_users(num_users, debug=debug, progress_callback=progress)

    print()  # New line after progress
    return stats
