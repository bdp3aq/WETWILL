# ClickyDraft Live Draft Assistant

Live recommendation tool for Bradley's **Wet Willie Brigade** Yahoo league
(14-team, H2H, keeper). It polls ClickyDraft's draft-app API during a real
draft and ranks the remaining player pool using this league's *actual*
custom Yahoo scoring settings — not generic ADP — combined with Bradley's
positional roster needs.

**By default, this tool never drafts anything** — it only reads from
ClickyDraft and prints recommendations to the console; picks are made by
Bradley, by hand, in the ClickyDraft UI. There's one narrow, **opt-in**
exception: an autopick safety net that can submit a pick as a last resort
if Bradley hasn't picked himself and his clock is about to expire. It's
off by default and requires deliberate, double opt-in to activate — see
**Autopick safety net** below before touching it.

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

## Autopick safety net (opt-in, off by default)

This tool's core purpose is recommendation-only — see `API_NOTES.md`'s
original spec. One narrow addition was made on top of that: an **opt-in
safety net** that can submit Bradley's own top recommendation as a last
resort, but only if he hasn't picked himself and his own clock is about
to run out. The point isn't to draft *for* him — it's so that a missed
slot (stepped away, lost connection, timer surprise) goes to this tool's
custom-scoring pick instead of to ClickyDraft's own generic autopick,
which knows nothing about this league's scoring.

**It is off by default**, and firing requires ALL of the following —
see `src/clickydraft_assistant/autopick.py` for the exact logic:

1. `autopick.enabled: true` in `config.yaml` (default `false`).
2. It's unambiguously Bradley's turn — inferred from the actual pick
   history (`turn.py`), never guessed. **Known limitation:** because this
   is inferred purely from observed picks, the tool can't know Bradley's
   round-1 slot until every team's round-1 pick has landed — so the
   safety net is inert for the entire first round and only becomes
   active from round 2 onward. This is intentional caution, not a bug.
3. A *confirmed* reading of seconds remaining on Bradley's clock, at or
   below `autopick.trigger_seconds_remaining` (default 10s). **This isn't
   wired up yet** — see "What's still missing" below. Until it is,
   `draft_timer.py` always reports "unknown," and by design an unknown
   timer state means the safety net never fires (an unknown state is
   treated as "don't act," not "assume it's urgent").
4. A genuine top recommendation exists with a real stat-based projection
   (never falls back to an ADP-only-ranked player, never submits nothing).
5. **Double opt-in for real submission:** even when all of the above
   line up, actually submitting a pick additionally requires passing
   `--confirm-autopick-submit` on the command line every time you run the
   tool. Without it, an armed decision only ever logs `[DRY RUN] Autopick
   would submit <player> now` — nothing is sent to ClickyDraft.

### What's still missing before this can submit anything for real

- **The pick-submission request is confirmed and implemented** — captured
  from a real successful pick in Bradley's own draft
  (`POST .../picks/`, see `API_NOTES.md` "5. Submit Pick"). `api_client.py`'s
  `submit_pick` sends the real request now, not a stub.
- **Where "seconds remaining" actually lives is still unconfirmed.**
  `draft_timer.py`'s `read_seconds_remaining` always returns `None` today.
  Use `scripts/watch_for_timer_field.py` during Bradley's own turn to spot
  it automatically (it diffs consecutive polls and prints whatever
  changes) — if nothing changes there while his clock visibly counts
  down, it likely only lives on the websocket stream this project
  otherwise intentionally skips, which would need a browser-based
  capture instead (DevTools → Network → filter to `WS` → Messages tab).

**This is now the only remaining blocker.** Once it's resolved, enabling
`autopick.enabled` + `--confirm-autopick-submit` will make the safety net
capable of actually submitting a pick — test that combination carefully
(e.g. on a late, low-stakes bench slot) before trusting it on a pick that
matters. Until then, enabling `autopick.enabled` is safe to leave on if
you want — condition 3 above will never be met, so it will only ever
print dry-run log lines, never act.

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

### Auth

**Confirmed** (see `API_NOTES.md`): cookie-based session auth (`JSESSIONID`,
optionally `rememberme`) — no bearer token or custom header needed.

1. Log into ClickyDraft in Chrome and open the league's draft room.
2. DevTools (F12) → Network tab → find any `draftapp/...` request →
   Request Headers → copy the full `Cookie` value.
3. Export it locally before running the tool — **never paste it into chat,
   commit it, or write it to a file**; it's a live session credential:
   ```bash
   export CLICKYDRAFT_COOKIE='paste the full cookie header here'
   ```

If a request comes back with an auth error, the tool will say so
explicitly (`ClickyDraftAuthError`) rather than silently returning empty
data — that means the cookie is missing or has expired and needs
re-capturing. If you ever paste or expose a cookie value by accident, log
out and back into ClickyDraft to invalidate it.

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

# Only relevant if config.yaml has autopick.enabled: true — required in
# addition to that before the safety net will actually submit a pick
# rather than just logging what it would have done:
clickydraft-assistant --confirm-autopick-submit
```

## Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/
```

Covers the scoring math (including the yardage bonus thresholds and DST
points-allowed tiers), keeper ingestion, pick diffing (including
`deleteAction`/`skipAction` handling), roster-needs slot filling, the
ranking/VOR logic, the ADP fallback ordering (including that it never
outranks a real projection), snake-order turn inference (including the
round/posInRound math that matches the real captured submission
request), the autopick safety net's decision logic (including all the
conditions that must hold before it fires), and `submit_pick`'s request
shape (mocked HTTP — no real network calls in tests).

## Known limitations / open items

Carried over from `API_NOTES.md`, still unresolved:

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
- **Autopick safety net is still dry-run only** — the pick-submission
  endpoint is now confirmed and implemented, but the "seconds remaining"
  timer source is still an unconfirmed stub, which by design keeps the
  safety net from ever firing for real. See "Autopick safety net" above.
- The websocket stream (`wss://stream1.clickydraft.com/ws/{leagueInstanceId}`)
  is intentionally not used, per the recommendation in `API_NOTES.md` —
  polling is simpler and avoids reconnect/parsing complexity.
