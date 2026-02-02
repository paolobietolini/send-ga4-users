"""GA4 Measurement Protocol client for sending events."""

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from config import GA4Config


@dataclass
class GA4Event:
    """Represents a GA4 event."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class GA4User:
    """Represents a GA4 user session."""

    client_id: str
    session_id: int
    user_id: str | None = None
    user_properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_new(cls, client_id: str, user_id: str | None = None) -> "GA4User":
        """Create a new user with a fresh session."""
        session_id = int(time.time())
        return cls(client_id=client_id, session_id=session_id, user_id=user_id)


class MeasurementProtocolClient:
    """Async client for GA4 Measurement Protocol."""

    def __init__(self, config: GA4Config, debug: bool = False):
        self.config = config
        self.debug = debug
        self._client: httpx.AsyncClient | None = None

    @property
    def endpoint(self) -> str:
        """Get the appropriate endpoint based on debug mode."""
        return self.config.debug_endpoint if self.debug else self.config.mp_endpoint

    async def __aenter__(self) -> "MeasurementProtocolClient":
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    async def send_event(self, user: GA4User, event: GA4Event) -> dict[str, Any]:
        """Send a single event to GA4."""
        return await self.send_events(user, [event])

    async def send_events(
        self, user: GA4User, events: list[GA4Event]
    ) -> dict[str, Any]:
        """Send multiple events to GA4."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        # Build payload
        payload = self._build_payload(user, events)

        # Send request
        response = await self._client.post(self.endpoint, json=payload)

        result = {
            "status_code": response.status_code,
            "success": response.status_code == 204 or response.status_code == 200,
        }

        # Debug endpoint returns validation info
        if self.debug and response.content:
            result["debug_response"] = response.json()

        return result

    def _build_payload(
        self, user: GA4User, events: list[GA4Event]
    ) -> dict[str, Any]:
        """Build the Measurement Protocol payload."""
        payload: dict[str, Any] = {
            "client_id": user.client_id,
            "events": [],
        }

        # Add user_id if present
        if user.user_id:
            payload["user_id"] = user.user_id

        # Add user properties if present
        if user.user_properties:
            payload["user_properties"] = {
                k: {"value": v} for k, v in user.user_properties.items()
            }

        # Add events with required session params
        for event in events:
            event_data = {
                "name": event.name,
                "params": {
                    **event.params,
                    "session_id": str(user.session_id),
                    "engagement_time_msec": event.params.get(
                        "engagement_time_msec", 100
                    ),
                },
            }
            payload["events"].append(event_data)

        return payload

    # Convenience methods for common events

    async def send_session_start(
        self, user: GA4User, page_location: str, page_title: str = ""
    ) -> dict[str, Any]:
        """Send session_start event."""
        event = GA4Event(
            name="session_start",
            params={
                "page_location": page_location,
                "page_title": page_title,
                "engagement_time_msec": 0,
            },
        )
        return await self.send_event(user, event)

    async def send_page_view(
        self,
        user: GA4User,
        page_location: str,
        page_title: str = "",
        page_referrer: str = "",
        engagement_time_msec: int = 100,
    ) -> dict[str, Any]:
        """Send page_view event."""
        event = GA4Event(
            name="page_view",
            params={
                "page_location": page_location,
                "page_title": page_title,
                "page_referrer": page_referrer,
                "engagement_time_msec": engagement_time_msec,
            },
        )
        return await self.send_event(user, event)

    async def send_user_engagement(
        self,
        user: GA4User,
        engagement_time_msec: int,
        page_location: str = "",
    ) -> dict[str, Any]:
        """Send user_engagement event."""
        event = GA4Event(
            name="user_engagement",
            params={
                "engagement_time_msec": engagement_time_msec,
                "page_location": page_location,
            },
        )
        return await self.send_event(user, event)

    async def send_first_visit(self, user: GA4User) -> dict[str, Any]:
        """Send first_visit event for new users."""
        event = GA4Event(
            name="first_visit",
            params={"engagement_time_msec": 0},
        )
        return await self.send_event(user, event)
