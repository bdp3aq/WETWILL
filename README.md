# ClickyDraft Live Draft Assistant

Live recommendation tool for Bradley's **Wet Willie Brigade** Yahoo league
(14-team, H2H, keeper). It polls ClickyDraft's draft-app API during a real
draft and ranks the remaining player pool using this league's *actual*
custom Yahoo scoring settings — not generic ADP — combined with Bradley's
positional roster needs.

**This tool never drafts anything.** It only reads from ClickyDraft and
prints recommendations to the console. Picks are made by Bradley, by hand,
in the ClickyDraft UI.

See `API_NOTES.md` for the full API/spec write-up this was built from.

## How it works

1. On startup: fetch League Settings (teams + roster rules) and the full
   Draftable Players pool, then fetch Picks once to ingest any preloaded
   **keeper** picks (`keeper: true`) — those players are removed from the
   pool and credited to rosters immediately, since this is a keeper league
   and keeper slots are locked in before the live draft opens.
2. During the draft: poll the Picks endpoint every 1–2 seconds, diff
   against the last poll, and update state — correctly ignoring
   `skipAction` picks (no player taken) and undoing `deleteAction` picks
   (a correction that un-drafts a player).
3. Recompute rankings on the remaining player pool:
   - **Projected points** = the league's custom point values (see
     `API_NOTES.md`) applied to each player's projected raw stats.
   - **VOR (value over replacement)** = a player's points minus the
     points of the replacement-level player still available at that
     position, so a great player at a deep position (e.g. WR) doesn't
     automatically outrank a merely-good player at a scarce one.
   - **Need bonus** = extra weight when a player would fill one of
     Bradley's still-open starting slots (bigger bonus for a dedicated
     slot than for only the flex spot).
4. Render a live top-N recommendation table plus a recent-picks feed.

## Setup

```bash
pip install -e .
cp config.example.yaml config.yaml
```

Edit `config.yaml`:
- `league_id` / `league_instance_id` are pre-filled for Bradley's league
  (305751 / 305775).
- `my_team_id` — Bradley's `fantasyTeamId` in this instance. If you don't
  know it yet, set `my_team_name` instead (must match `teamName` exactly
  from League Settings) and the tool resolves the ID on startup.
- `projections_csv` — see **Player projections** below.

### Auth (open item — confirm before a live draft)

ClickyDraft's auth mechanism isn't documented publicly. The working
assumption (see `API_NOTES.md`) is a session cookie:

1. Log into ClickyDraft in Chrome and open the league's draft room.
2. DevTools (F12) → Network tab → find any `draftapp/...` request →
   Request Headers → copy the full `Cookie` value.
3. Export it before running the tool:
   ```bash
   export CLICKYDRAFT_COOKIE='paste the full cookie header here'
   ```

If a request comes back with an auth error, the tool will say so
explicitly (`ClickyDraftAuthError`) rather than silently returning empty
data — that means the cookie is missing or has expired and needs
re-capturing.

### Player projections

The one sample ClickyDraft payload we have shows `draftablePlayer.projectedStats`
as `null`. If that's still empty for a live league instance, the ranking
engine needs an external source of projected raw stats. Two options:

1. **Preferred if it works:** if ClickyDraft *does* populate
   `projectedStats` for this league with recognizable stat keys, the tool
   uses it automatically — no CSV needed.
2. **Fallback:** put a CSV at the path in `projections_csv`
   (`data/projections.csv` by default) with one row per player. See
   `data/projections.example.csv` for the exact column format — columns
   are raw per-player stat projections (`pass_yds`, `rec`, `rush_td`,
   `points_allowed`, etc.), matched to players by name (and team, to
   disambiguate). Any stat scoring.py doesn't recognize is ignored;
   missing stats default to 0.

Players with no projection available at all still show up in the table
(flagged with `—`) rather than being silently dropped, so nothing
disappears from the board unexpectedly mid-draft.

### Fallback ranking (generic ADP — for players with no projection only)

`data/Top-144 Player Rankings.xlsx` (Bradley-supplied) is a generic
overall-rank/ADP list — no positions, no raw stats, and it's standard PPR
scoring rather than this league's custom point values. Per the whole
premise of this project (see `API_NOTES.md`: "generic ADP/rankings won't
cut it"), it must never override the custom point-value ranking above.

It's wired in as a **fallback ordering only**: for a player with no
stat-based projection at all, the tool uses this file's rank (averaged
across its two sheets if the player appears on both) just to give that
player a sane position on the board relative to other unprojected
players. Any player with a real projection always outranks every
fallback-only player, regardless of ADP. Rows using this fallback are
marked `ADP fallback (#N)` in the Score column so it's clear at a glance
which recommendations are backed by the real scoring model and which
aren't. Configure the path via `fallback_rankings_xlsx` in `config.yaml`
(set it to `null`/omit to disable fallback ordering entirely).

## Running it

```bash
# Single poll, print once and exit — good for testing config/auth without
# babysitting a live draft:
clickydraft-assistant --once

# Live polling loop (default config.yaml path):
clickydraft-assistant

# Custom config path:
clickydraft-assistant --config path/to/config.yaml
```

## Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/
```

Covers the scoring math (including the yardage bonus thresholds and DST
points-allowed tiers), keeper ingestion, pick diffing (including
`deleteAction`/`skipAction` handling), roster-needs slot filling, the
ranking/VOR logic, and the ADP fallback ordering (including that it never
outranks a real projection).

## Known limitations / open items

Carried over from `API_NOTES.md`, still unresolved:

- **Auth** hasn't been confirmed against a live ClickyDraft session yet.
- **Roster construction field names** in the real League Settings response
  aren't confirmed — `roster.py` currently hard-codes the roster from the
  spec (QB, WR×2, RB×2, TE, FLEX, K, DEF, 7 bench) rather than reading it
  from the API. Once a real response is captured, wire `compute_roster_needs`
  up to the actual settings payload instead.
- Whether preloaded keeper picks are visible on the Picks endpoint *before*
  the draft opens (vs. only once it starts) hasn't been confirmed against
  a live instance — `ingest_keepers` assumes they are.
- **Player projections**: no projections source is wired up beyond the
  CSV fallback — `data/projections.csv` needs to be populated with real
  season projections before a live draft (see above).
- The websocket stream (`wss://stream1.clickydraft.com/ws/{leagueInstanceId}`)
  is intentionally not used, per the recommendation in `API_NOTES.md` —
  polling is simpler and avoids reconnect/parsing complexity.
