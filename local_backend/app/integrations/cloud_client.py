"""HTTP client for the central cloud platform (Django API v2).

The local backend is an Edge Agent: it talks to the hardware, to the local
SQLite database and to the cloud. This module owns the *cloud* side only.

Design notes (KISS):

* A single :class:`CloudClient` wraps ``httpx`` with a base URL, a Bearer
  token and a request timeout taken from :data:`app.core.config.config`.
* Every call attaches an ``X-Request-ID`` header so a request can be traced
  end to end across the terminal and the cloud.
* Network problems never propagate as raw exceptions to the caller: each
  method returns a :class:`CloudResult` describing what happened. This keeps
  the FastAPI process alive even when the cloud is unreachable.
* :class:`CloudClientError` is reserved for programmer/config errors (e.g.
  calling the client while it is not configured) and is *not* raised during
  normal request handling.

The cloud endpoints used here are the existing API v2 terminal endpoints:

* ``GET  terminal/ping``           – auth / connectivity check;
* ``POST terminal/scan-code/``     – confirm a pickup right;
* ``POST terminal/issue-events/``  – idempotent issue events.

``get_available_pickups`` / ``start_pickup`` target forward-looking v2
endpoints; they degrade gracefully if the cloud does not expose them yet.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import config

logger = logging.getLogger(__name__)


class CloudClientError(Exception):
    """Misconfiguration / programmer error (not a network failure)."""


@dataclass(frozen=True)
class CloudResult:
    """Outcome of a single cloud call.

    ``ok`` is True only for a 2xx response. ``retriable`` marks transient
    failures (network/timeout/5xx) for which the caller should keep the
    event PENDING instead of marking it permanently FAILED.
    """

    ok: bool
    status_code: int | None = None
    data: Any = None
    error: str | None = None
    retriable: bool = False


@dataclass(frozen=True)
class _EventLike:
    """Minimal structural contract :meth:`send_issue_event` relies on."""

    local_event_id: str | None
    event_type: str
    cell_number: int | None
    operation_id: int | None
    payload: dict = field(default_factory=dict)


class CloudClient:
    """Thin, fail-safe HTTP client for the cloud API v2."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout_seconds: float | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._base_url = (base_url or config.cloud_api_base_url).rstrip("/")
        self._token = token if token is not None else config.terminal_token
        self._timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else config.cloud_timeout_seconds
        )
        self._enabled = (
            enabled if enabled is not None else config.cloud_sync_enabled
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """Whether the client is configured well enough to attempt calls.

        This is a cheap, local check (no network): sync must be enabled and a
        terminal token must be present. Actual reachability is reported by the
        individual call results.
        """
        return bool(self._enabled and self._token and self._base_url)

    def ping(self, request_id: str) -> CloudResult:
        """Check connectivity / token validity against the cloud.

        Maps to ``GET /api/v2/terminal/ping``. A real network round-trip:
        ``result.ok`` is True only when the cloud answered 2xx. Used by the
        online-sales pickup flow to decide whether the terminal is online.
        """
        return self._request("GET", "/terminal/ping", request_id=request_id)

    def pickup_start(self, request_id: str) -> CloudResult:
        """Start an online-sales pickup at this terminal.

        Maps to ``POST /api/v2/terminal/pickup/start/``. The cloud decides
        which cells must be opened and returns them in the response body.
        Degrades gracefully (never raises) if the endpoint is not reachable.
        """
        return self._request(
            "POST", "/terminal/pickup/start/", request_id=request_id, json={}
        )

    def get_available_pickups(self, request_id: str) -> list:
        """Return the list of pickups available at this terminal.

        Targets a forward-looking v2 endpoint. On any failure returns an
        empty list (never raises), so the caller/UI stays responsive.
        """
        result = self._request(
            "GET", "/terminal/pickups/", request_id=request_id
        )
        if not result.ok:
            return []
        data = result.data
        if isinstance(data, dict):
            pickups = data.get("data", data)
            return pickups if isinstance(pickups, list) else []
        return data if isinstance(data, list) else []

    def start_pickup(self, request_id: str) -> CloudResult:
        """Ask the cloud to start a pickup (forward-looking v2 endpoint)."""
        return self._request(
            "POST", "/terminal/pickups/start/", request_id=request_id, json={}
        )

    def scan_code(self, code: str, method: str, request_id: str) -> CloudResult:
        """Confirm a pickup right for a scanned/entered code.

        Maps to ``POST /api/v2/terminal/scan-code/``.
        """
        return self._request(
            "POST",
            "/terminal/scan-code/",
            request_id=request_id,
            json={"code": code, "method": method},
        )

    def send_issue_event(self, event: Any) -> CloudResult:
        """Send a single issue event to the cloud (idempotent on the server).

        Maps to ``POST /api/v2/terminal/issue-events/``. ``event`` may be an
        :class:`app.repositories.event_repository.EventRecord` or any object
        exposing ``local_event_id``, ``event_type``, ``cell_number``,
        ``operation_id`` and ``payload`` (dict).
        """
        body = self._build_event_body(event)
        request_id = body["local_event_id"] or str(uuid.uuid4())
        return self._request(
            "POST",
            "/terminal/issue-events/",
            request_id=request_id,
            json=body,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _build_event_body(event: Any) -> dict:
        payload = getattr(event, "payload", None)
        if not isinstance(payload, dict):
            payload = {}
        operation_id = getattr(event, "operation_id", None)
        issue_operation_id = payload.get("issue_operation_id")
        if not issue_operation_id and operation_id is not None:
            issue_operation_id = str(operation_id)
        return {
            "local_event_id": getattr(event, "local_event_id", None),
            "issue_operation_id": issue_operation_id or "",
            "event_type": getattr(event, "event_type", ""),
            "cell_number": getattr(event, "cell_number", None),
            "payload": payload,
        }

    def _headers(self, request_id: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "X-Request-ID": request_id,
            "X-Terminal-ID": config.terminal_id,
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        request_id: str,
        json: dict | None = None,
    ) -> CloudResult:
        """Perform one HTTP call, converting all errors into a CloudResult."""
        if not self.is_available():
            return CloudResult(
                ok=False,
                error="cloud sync disabled or terminal token missing",
                retriable=True,
            )

        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.request(
                    method,
                    url,
                    json=json,
                    headers=self._headers(request_id),
                )
        except httpx.TimeoutException as exc:
            logger.warning("cloud request timeout %s %s: %s", method, url, exc)
            return CloudResult(ok=False, error=f"timeout: {exc}", retriable=True)
        except httpx.HTTPError as exc:
            logger.warning("cloud request failed %s %s: %s", method, url, exc)
            return CloudResult(
                ok=False, error=f"network error: {exc}", retriable=True
            )

        return self._to_result(response)

    @staticmethod
    def _to_result(response: httpx.Response) -> CloudResult:
        try:
            data = response.json()
        except ValueError:
            data = response.text

        if response.is_success:
            return CloudResult(ok=True, status_code=response.status_code, data=data)

        # 5xx -> transient (retriable). 4xx -> permanent (do not retry).
        retriable = response.status_code >= 500
        message = None
        if isinstance(data, dict):
            message = data.get("message") or data.get("code")
        return CloudResult(
            ok=False,
            status_code=response.status_code,
            data=data,
            error=message or f"HTTP {response.status_code}",
            retriable=retriable,
        )


def get_cloud_client() -> CloudClient:
    """Factory used as a dependency / by the sync service."""
    return CloudClient()
