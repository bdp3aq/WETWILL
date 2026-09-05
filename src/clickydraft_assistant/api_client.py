"""HTTP client for the (undocumented) ClickyDraft draft-app API.

Auth is confirmed cookie-based (see API_NOTES.md "Authentication") — a
`JSESSIONID` session cookie, no bearer token or custom header. This client
authenticates by replaying a raw `Cookie` header captured from a
logged-in browser session (DevTools -> Network -> any draftapp request ->
Request Headers -> Cookie). Pass it via the `CLICKYDRAFT_COOKIE` env var
(see config.py) or the `cookie` constructor argument. Treat that value as
a live credential — never log it, write it to a file, or commit it.

`submit_pick` is a real write call, confirmed against a request captured
from Bradley's own live draft session (see its docstring) — it is not a
guess. It still only ever gets called from the opt-in autopick safety net
(autopick.py), which stays gated behind config + a CLI flag + a confirmed
timer reading.
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

    def submit_pick(
        self,
        fantasy_team_id: int,
        draftable_player_id: int,
        round_number: int,
        pos_in_round: int,
        keeper: bool = False,
        auto_drafted: bool = False,
    ) -> dict:
        """Submit a real draft pick. USED ONLY by the opt-in autopick safety
        net (autopick.py), and only ever as a last resort when Bradley hasn't
        picked himself and his clock is about to expire — see that module's
        docstring for the full safety gating.

        Confirmed against a request captured from Bradley's own live draft
        session (a real successful pick, round 8 posInRound 7) — this is not
        a guess:

            POST {base_url}/leagues/{leagueId}/league-instances/{leagueInstanceId}/picks/
            Content-Type: application/json
            X-Requested-With: XMLHttpRequest
            {
              "leagueId": ..., "leagueInstanceId": ...,
              "fantasyTeamId": ..., "draftablePlayerId": ...,
              "round": ..., "posInRound": ...,
              "keeper": false, "autoDrafted": false,
              "id": null, "value": null, "skipped": null
            }

        `round`/`pos_in_round` are NOT inferred here — pass them from
        `turn.round_and_pos_in_round(overall_pick_number, num_teams)` so the
        caller's own turn-tracking is the single source of truth for "which
        slot is this." `auto_drafted` defaults to False because this mirrors
        a normal manual pick (a specific, deliberately chosen player) just
        submitted by the tool instead of a browser click — not ClickyDraft's
        own random autopick.

        Deliberately does NOT retry on failure (unlike `_get`): retrying a
        write call risks submitting the same pick twice if the first attempt
        actually succeeded server-side but the response was lost. A failure
        here should be surfaced to Bradley immediately, not silently retried.
        """
        url = f"{self.base_url}/leagues/{self.league_id}/league-instances/{self.league_instance_id}/picks/"
        body = {
            "leagueId": self.league_id,
            "leagueInstanceId": self.league_instance_id,
            "fantasyTeamId": fantasy_team_id,
            "draftablePlayerId": draftable_player_id,
            "round": round_number,
            "posInRound": pos_in_round,
            "keeper": keeper,
            "autoDrafted": auto_drafted,
            "id": None,
            "value": None,
            "skipped": None,
        }
        try:
            response = self._session.post(
                url,
                json=body,
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ClickyDraftAPIError(f"Failed to POST {url}: {exc}") from exc

        if response.status_code in (401, 403):
            raise ClickyDraftAuthError(
                f"{response.status_code} from {url} — the CLICKYDRAFT_COOKIE is likely "
                "missing or expired. Re-capture it from DevTools -> Network."
            )
        if not response.ok:
            raise ClickyDraftAPIError(f"{response.status_code} from {url}: {response.text[:500]}")
        return response.json()
