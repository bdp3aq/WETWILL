# ClickyDraft Live Draft Assistant

Live recommendation tool for Bradley's Wet Willie Brigade 14-team keeper
league. Polls ClickyDraft's draft-app API during a live draft and ranks
the remaining player pool using this league's custom Yahoo scoring
settings + positional roster needs. Recommendation-first: manual picking
in the ClickyDraft UI is the default and primary mode. One narrow, opt-in
exception exists — see Conventions below.

Full spec, API endpoints, scoring table, and open questions live in
`API_NOTES.md` — read that first for any work on this project, including
the scope-amendment note at the top.

## Layout

- `src/clickydraft_assistant/scoring.py` — custom point-value engine
  (`ScoringSettings` mirrors the league's Yahoo scoring table).
- `src/clickydraft_assistant/projections.py` — per-player projected stat
  lookup (CSV fallback, since ClickyDraft's own `projectedStats` field is
  unconfirmed/empty).
- `src/clickydraft_assistant/state.py` — draft state: keeper ingestion,
  available player pool, roster tracking, pick diffing
  (`deleteAction`/`skipAction` handling).
- `src/clickydraft_assistant/roster.py` — roster slot construction and
  open-need computation.
- `src/clickydraft_assistant/ranking.py` — VOR + need-bonus ranking.
- `src/clickydraft_assistant/fallback_rankings.py` — generic-ADP fallback
  ordering (from `data/Top-144 Player Rankings.xlsx`) for players with no
  stat-based projection only — must never outrank a real projection.
- `src/clickydraft_assistant/turn.py` — infers whose turn it is from
  observed pick history (snake order), plus `round_and_pos_in_round` for
  the fields `submit_pick` needs. Used only by the autopick safety net.
- `src/clickydraft_assistant/turn_clock.py` — `TurnClock`: wall-clock idle
  time on the current turn, since ClickyDraft doesn't expose a
  discoverable countdown timer (confirmed via
  `scripts/watch_for_timer_field.py`). This is what the autopick safety
  net's wait threshold is measured against instead.
- `src/clickydraft_assistant/autopick.py` — the opt-in autopick safety
  net's decision logic (`evaluate_autopick`). Read its module docstring
  in full before changing anything here.
- `src/clickydraft_assistant/api_client.py` — cookie-auth HTTP client for
  the three ClickyDraft REST endpoints, plus `submit_pick` — a real write
  call confirmed against a captured live request (see API_NOTES.md "5.
  Submit Pick"), used only by the autopick safety net.
- `src/clickydraft_assistant/cli.py` / `display.py` — polling loop + rich
  console output; wires the autopick decision into the loop with a
  `--confirm-autopick-submit` double-opt-in flag.
- `scripts/inspect_api.py` — one-off recon script for confirming auth and
  real field names against a live session; not part of the tool itself.
- `tests/` — unit tests (`python -m pytest tests/`).

## Conventions

- **Recommendation display is the default and only always-on behavior.**
  The one exception is the autopick safety net (`autopick.py`), which
  Bradley explicitly requested: it may submit his own top recommendation,
  but ONLY as an opt-in last resort (off by default, and gated behind
  both `config.yaml`'s `autopick.enabled` AND the `--confirm-autopick-submit`
  CLI flag) when he hasn't picked himself for a while on his own turn.
  Do not build anything beyond that narrow scope — no drafting for other
  teams, no "just autopick the whole draft" mode, no removing the double
  opt-in, the one-fire-per-slot guard in `cli.py`, or the safety
  conditions in `evaluate_autopick`. Anything else that calls a
  ClickyDraft write endpoint needs the same explicit user sign-off this
  feature got before being added.
- Both prerequisites for the autopick safety net are resolved:
  `submit_pick` (api_client.py) is a real implementation confirmed against
  a captured live request, and the trigger mechanism is wall-clock idle
  time (`turn_clock.py`) since ClickyDraft doesn't expose a discoverable
  timer. If a future change needs another guessed write endpoint or
  unconfirmed field, apply the same standard those two met: capture and
  confirm it against a real live session first — never guess at a write
  endpoint against a real, consequential keeper-league draft.
- Never remove the `already_attempted_pick_number` guard in `cli.py`'s
  poll loop, and never make the autopick path retry a failed
  `submit_pick` automatically — a lagging `get_picks()` response after a
  successful submit, or a naive retry after a failure, both risk a
  duplicate real pick. A failed submission must surface loudly and stop,
  not retry or fail silently.
- Scoring values are data (`ScoringSettings` fields), not magic numbers
  scattered through code — if the league's settings change, they should
  only need to change in one place.
- Treat any ClickyDraft session cookie as a live credential: never log
  it, write it to a file, or commit it — env var only (`CLICKYDRAFT_COOKIE`).
- See README.md's "Known limitations" for unresolved items (real
  roster-construction field names, keeper-preload timing) before assuming
  the API integration is fully verified against a live ClickyDraft
  session — it hasn't been for those items.
