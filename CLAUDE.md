# ClickyDraft Live Draft Assistant

Live recommendation tool (no auto-draft) for Bradley's Wet Willie Brigade
14-team keeper league. Polls ClickyDraft's draft-app API during a live
draft and ranks the remaining player pool using this league's custom
Yahoo scoring settings + positional roster needs.

Full spec, API endpoints, scoring table, and open questions live in
`API_NOTES.md` — read that first for any work on this project.

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
- `src/clickydraft_assistant/api_client.py` — cookie-auth HTTP client for
  the three ClickyDraft REST endpoints.
- `src/clickydraft_assistant/cli.py` / `display.py` — polling loop + rich
  console output.
- `tests/` — unit tests (`python -m pytest tests/`).

## Conventions

- No auto-draft / auto-submit, ever — this tool only displays
  recommendations. Don't add anything that calls a ClickyDraft write
  endpoint.
- Scoring values are data (`ScoringSettings` fields), not magic numbers
  scattered through code — if the league's settings change, they should
  only need to change in one place.
- See README.md's "Known limitations" for unresolved items (auth
  mechanism, real roster-construction field names, keeper-preload timing)
  before assuming the API integration is fully verified against a live
  ClickyDraft session — it hasn't been yet.
