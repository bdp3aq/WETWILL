"""HTTP client for the (undocumented) ClickyDraft draft-app API.

Auth is confirmed cookie-based (see API_NOTES.md "Authentication") — a
`JSESSIONID` session cookie, no bearer token or custom header. This client
authenticates by replaying a raw `Cookie` header captured from a
logged-in browser session (DevTools -> Network -> any draftapp request ->
Request Headers -> Cookie). Pass it via the `CLICKYDRAFT_COOKIE` env var
(see config.py) or the `cookie` constructor argument. Treat that value as
a live credential — never log it, write it to a file, or commit it.

`submit_pick` below is a deliberate stub, not a real write call — see its
docstring before touching it.
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

    def submit_pick(self, draftable_player_id: int, fantasy_team_id: int) -> dict:
        """Submit a real draft pick. USED ONLY by the opt-in autopick safety
        net (autopick.py), and only ever as a last resort when Bradley hasn't
        picked himself and his clock is about to expire — see that module's
        docstring for the full safety gating.

        This is intentionally unimplemented: the three GET endpoints in
        API_NOTES.md were all captured by observing Bradley's own browser
        traffic, but no one has captured the request ClickyDraft's UI sends
        when a pick is *submitted* (method, path, body shape are all
        unknown). Guessing at a write endpoint and firing it against a real,
        consequential keeper-league draft is exactly the kind of mistake
        this tool exists to avoid.

        To implement this for real:
          1. During a real or practice draft, open DevTools -> Network,
             make a pick through the ClickyDraft UI, and find the request
             it fires (likely a POST/PUT to something under
             `/leagues/{leagueId}/league-instances/{leagueInstanceId}/picks`).
          2. Capture its method, full URL, and request body shape.
          3. Replace this method's body with the real `self._session.post(...)`
             (or put/patch) call, keeping the same auth/retry pattern as `_get`.
          4. Test it against a low-stakes situation first if at all possible
             (e.g. a spare late-round bench slot) before trusting it in a
             pick that matters.
        """
        raise NotImplementedError(
            "submit_pick is a stub — the real ClickyDraft pick-submission endpoint hasn't "
            "been captured yet. See this method's docstring for how to capture and wire it up. "
            "Until then the autopick safety net can only run in dry-run mode."
        )
