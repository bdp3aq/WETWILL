"""HTTP client for the (undocumented) ClickyDraft draft-app API.

Auth is unconfirmed (see API_NOTES.md "Authentication") — the calls were
only ever observed via the browser Network tab. Until that's nailed down,
this client authenticates by replaying a raw `Cookie` header captured from
a logged-in browser session (DevTools -> Network -> any draftapp request ->
Request Headers -> Cookie). Pass it via the `CLICKYDRAFT_COOKIE` env var
(see config.py) or the `cookie` constructor argument.

If ClickyDraft turns out to use a bearer token instead, swap the
`_session.headers["Cookie"]` line for an `Authorization` header — everything
else here stays the same.
"""

from __future__ import annotations

import time
from typing import Any

import requests

BASE_URL = "https://clickydraft.com/draftapp"
DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 1.5


class ClickyDraftAuthError(RuntimeError):
    """Raised on 401/403 — the captured cookie is missing or has expired."""


class ClickyDraftAPIError(RuntimeError):
    pass


class ClickyDraftClient:
    def __init__(
        self,
        league_id: int,
        league_instance_id: int,
        cookie: str | None = None,
        base_url: str = BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ):
        self.league_id = league_id
        self.league_instance_id = league_instance_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        if cookie:
            self._session.headers["Cookie"] = cookie
        self._session.headers.setdefault(
            "User-Agent",
            "clickydraft-assistant/0.1 (+live draft recommendation tool)",
        )

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRIES + 1):
            try:
                response = self._session.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
            else:
                if response.status_code in (401, 403):
                    raise ClickyDraftAuthError(
                        f"{response.status_code} from {url} — the CLICKYDRAFT_COOKIE is "
                        "likely missing or expired. Re-capture it from DevTools -> Network."
                    )
                if response.ok:
                    return response.json()
                last_error = ClickyDraftAPIError(f"{response.status_code} from {url}: {response.text[:200]}")
            if attempt < DEFAULT_RETRIES:
                time.sleep(DEFAULT_BACKOFF_SECONDS * attempt)
        raise ClickyDraftAPIError(f"Failed to GET {url} after {DEFAULT_RETRIES} attempts: {last_error}")

    def get_league_settings(self) -> dict:
        return self._get(f"/leagues/{self.league_id}/league-instances/{self.league_instance_id}")

    def get_picks(self) -> list[dict]:
        return self._get(f"/leagues/{self.league_id}/league-instances/{self.league_instance_id}/picks")

    def get_draftable_players(self) -> list[dict]:
        return self._get(
            f"/leagues/{self.league_id}/league-instances/{self.league_instance_id}/draftable-players"
        )
