"""Live draft state: player pool, rosters, and pick diffing.

Handles the keeper-preload step and the deleteAction/skipAction pick flags
called out in API_NOTES.md:

- On first load, `keeper: true` picks are already-applied picks (the draft
  hasn't started yet, but keeper slots are locked in) — they must be
  removed from the available pool and credited to rosters immediately.
- A `deleteAction: true` pick undoes a previously-applied pick (a
  commissioner or the app corrected a mistake) — the player goes back to
  the available pool.
- A `skipAction: true` pick consumes a draft slot but no player — it's
  never "applied" to a roster.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Pick, Player, Team


@dataclass
class PickEvent:
    """A change detected on the latest poll, for the display's live feed."""

    kind: str  # "pick" | "undo"
    pick: Pick


class DraftState:
    def __init__(self, players: list[Player], teams: list[Team]):
        self.players_by_id: dict[int, Player] = {p.draftable_player_id: p for p in players}
        self.teams_by_id: dict[int, Team] = {t.id: t for t in teams}

        self.available_player_ids: set[int] = set(self.players_by_id.keys())
        self.rosters: dict[int, list[Pick]] = {team_id: [] for team_id in self.teams_by_id}

        # Picks currently counted as "applied" (real, non-deleted, non-skipped), by pick id.
        self._applied_picks: dict[int, Pick] = {}
        # Every pick id we've seen at all, regardless of state, so we can detect deletions.
        self._last_seen: dict[int, Pick] = {}

    def team_name(self, fantasy_team_id: int) -> str:
        team = self.teams_by_id.get(fantasy_team_id)
        return team.team_name if team else f"Team {fantasy_team_id}"

    def roster_players(self, fantasy_team_id: int) -> list[Player]:
        players = []
        for pick in self.rosters.get(fantasy_team_id, []):
            player = self.players_by_id.get(pick.draftable_player_id)
            if player:
                players.append(player)
        return players

    def _apply(self, pick: Pick) -> None:
        self._applied_picks[pick.id] = pick
        self.available_player_ids.discard(pick.draftable_player_id)
        self.rosters.setdefault(pick.fantasy_team_id, []).append(pick)

    def _unapply(self, pick_id: int) -> None:
        pick = self._applied_picks.pop(pick_id, None)
        if pick is None:
            return
        self.available_player_ids.add(pick.draftable_player_id)
        roster = self.rosters.get(pick.fantasy_team_id, [])
        self.rosters[pick.fantasy_team_id] = [p for p in roster if p.id != pick_id]

    def ingest_keepers(self, picks: list[Pick]) -> int:
        """Startup-only: apply preloaded keeper picks before the live draft begins.
        Returns the number of keeper picks applied.
        """
        count = 0
        for pick in picks:
            self._last_seen[pick.id] = pick
            if pick.keeper and pick.is_real_pick and pick.id not in self._applied_picks:
                self._apply(pick)
                count += 1
        return count

    def update(self, picks: list[Pick]) -> list[PickEvent]:
        """Diff a fresh poll of the Picks endpoint against known state.
        Returns the list of changes (new picks applied, previous picks undone).
        """
        events: list[PickEvent] = []
        current_ids = set()

        for pick in picks:
            current_ids.add(pick.id)
            previously_applied = pick.id in self._applied_picks
            self._last_seen[pick.id] = pick

            if pick.is_real_pick:
                if not previously_applied:
                    self._apply(pick)
                    events.append(PickEvent(kind="pick", pick=pick))
                # else: unchanged, nothing to do.
            else:
                # deleteAction or skipAction: make sure it's not counted as applied.
                if previously_applied:
                    self._unapply(pick.id)
                    events.append(PickEvent(kind="undo", pick=pick))

        # Picks that vanished entirely from the feed (rare, but be defensive).
        vanished = set(self._applied_picks.keys()) - current_ids
        for pick_id in vanished:
            pick = self._applied_picks[pick_id]
            self._unapply(pick_id)
            events.append(PickEvent(kind="undo", pick=pick))

        return events

    def available_players(self) -> list[Player]:
        return [self.players_by_id[pid] for pid in self.available_player_ids]
