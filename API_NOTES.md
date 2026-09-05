# ClickyDraft Live Draft Assistant — Project Instructions

Seed document for the Claude Code build. Starting context for this project.

## Goal

Build a tool that connects to ClickyDraft's live draft data during a real draft and continuously recomputes player rankings using a custom point-value system tied to this league's scoring settings (not generic ADP or default projections), so Bradley can make better picks in real time. **Scope is live recommendation surfacing only — no auto-draft / auto-submit.** Draft results get uploaded into Yahoo afterward for scoring, so the ranking logic should reflect Yahoo scoring settings for this league.

## Bradley's League

- League dashboard URL: `https://clickydraft.com/draftapp/dashboard/leagues/305751/instances/305775`
- Live draft board URL: `https://clickydraft.com/draftapp/board/305775` — the actual draft-room page Bradley uses during the live draft. Note the different path shape: `draftapp/board/{leagueInstanceId}` takes only the instance ID, no league ID segment — consistent with the API endpoints below, which mostly key off the instance ID too.
- **League ID:** `305751`
- **League Instance ID:** `305775`

(Everywhere below, substitute these for `{leagueId}` / `{leagueInstanceId}`.)

## League Format (Yahoo)

- **League:** Wet Willie Brigade (Yahoo League ID 928832)
- 14 teams, Head-to-Head scoring, Keeper League (this explains the `keeper` flag on picks — keeper picks should probably be weighted/handled differently than open-draft picks)
- Draft happens off-platform on ClickyDraft ("Offline Draft" on Yahoo). **Draft format is confirmed snake** (not auction).
- Fractional points: yes. Negative points: yes.
- **Roster positions (16 slots):** QB, WR, WR, RB, RB, TE, W/R/T, K, DEF, BN, BN, BN, BN, BN, BN, BN (7 bench slots)

## League Scoring (Yahoo — this is the point-value system the rankings should be built against)

**Offense**

| Stat | League Value |
|---|---|
| Completions | 0.125 |
| Passing Yards | 20 yards/pt; +20 pt bonus at 555 yds |
| Passing TD | 5 |
| Interception (thrown) | -2 |
| Rushing Yards | 10 yards/pt; +3 pt at 100 yds, +3 pt at 200 yds, +20 pt at 297 yds |
| Rushing TD | 6 |
| Receptions | 0.33 |
| Receiving Yards | 10 yards/pt; +4 pt at 100 yds, +4 pt at 200 yds, +20 pt at 337 yds |
| Receiving TD | 6 |
| Return TD | 6 |
| 2-Point Conversion | 2 |
| Fumble Lost | -2 |
| Offensive Fumble Return TD | 6 |

**Kickers**

| Stat | League Value |
|---|---|
| FG 0-19 yds | 1 |
| FG 20-29 yds | 2 |
| FG 30-39 yds | 3 |
| FG 40-49 yds | 4 |
| FG 50+ yds | 5 |
| Missed FGs (any distance) | 0 |
| PAT Made | 1 |
| PAT Missed | 0 |

**Defense / Special Teams**

| Stat | League Value |
|---|---|
| Sack | 1 |
| Interception | 2 |
| Fumble Recovery | 2 |
| Touchdown | 5.1 |
| Safety | 2 |
| Block Kick | 1.7 |
| Kickoff/Punt Return TD | 6 |
| Points Allowed: 0 | 12.75 |
| Points Allowed: 1-6 | 8.5 |
| Points Allowed: 7-13 | 5.97 |
| Points Allowed: 14-20 | 2.55 |
| Points Allowed: 21-27 | 0.85 |
| Points Allowed: 28-34 | 0 |
| Points Allowed: 35+ | -2 |
| 4th Down Stops | 1 |
| Three-and-Outs Forced | 1 |
| Extra Point Returned | 2 |

Notice several of these deviate meaningfully from Yahoo defaults (e.g. passing TD 5 vs 4, reception 0.33 vs 0.5, rushing/receiving yardage bonuses, DST points-allowed tiers) — this is exactly why generic ADP/rankings won't cut it and a custom point-value model per this table is the point of the project.

## Background on the two IDs

Every ClickyDraft URL carries two IDs: a **league id** and a **league instance id**. Historically ClickyDraft let you create multiple draft boards per league (same settings, different "instance"), which added complexity for little benefit and was scrapped early on. So today the two IDs almost always point at the same underlying thing — but both still show up in URLs, and most of the data calls key off the **instance id**, not the league id.

## Authentication

Not documented in what was provided — the calls below were captured via the browser, so they're likely riding on a session cookie rather than a bearer token. **Open item:** open Chrome DevTools → Network tab (F12) on a live ClickyDraft session and check the request headers on any of the calls below (especially `Cookie`, and any custom header) to confirm how auth works before building a standalone client.

## Endpoints

### 1. League Settings

```
GET https://clickydraft.com/draftapp/leagues/{leagueId}/league-instances/{leagueInstanceId}
```

Notable fields:
- `leagueUsers` — array of league users (may or may not be useful).
- `fantasyTeams` — array of teams; grab each team's `id` and `teamName`. Needed to resolve `fantasyTeamId` on picks into a human-readable team name.
- (Roster construction / scoring settings likely live here too — confirm exact field names once a real response is captured.)

### 2. Picks

```
GET https://clickydraft.com/draftapp/leagues/{leagueId}/league-instances/{leagueInstanceId}/picks
```

Example object:

```json
{
  "id": 5336698,
  "leagueId": 79860,
  "leagueInstanceId": 79884,
  "fantasyTeamId": 859666,
  "draftablePlayerId": 11842,
  "draftablePlayer": {
    "id": 9501,
    "draftablePlayerId": 11842,
    "firstName": "David",
    "lastName": "Johnson",
    "exp": 3,
    "teamFullName": "Arizona Cardinals",
    "teamAbbr": "ARI",
    "positions": ["RB"],
    "attrs": null,
    "projectedStats": null,
    "byeWeek": 8,
    "sport": "NFL"
  },
  "value": 0,
  "round": 1,
  "posInRound": 1,
  "keeper": false,
  "autoDrafted": false,
  "deleteAction": false,
  "skipAction": false,
  "draftTimer": null
}
```

Notable fields:
- `fantasyTeamId` — look up against `fantasyTeams` from the League Settings call to get the team name.
- `round`, `posInRound` — draft slot bookkeeping.
- `keeper`, `autoDrafted`, `deleteAction`, `skipAction` — pick state flags; a real "pick" for ranking purposes should probably exclude anything with `deleteAction: true`.
- `draftablePlayer` — embedded player object, generally sufficient on its own. Note it carries its own `id` (9501) distinct from the top-level `draftablePlayerId` (11842) — worth confirming which one is stable/canonical before joining against the player list.
- `value` — used for auction-format drafts; not relevant here since this league is snake (expect 0 on every pick).
- **Keepers:** this is a keeper league, so on the very first poll of the Picks endpoint — before the live draft even starts — expect the keeper slots to already be preloaded as pick records with `keeper: true`. The tool needs to read these on startup and treat them exactly like any other pick: remove those players from the available pool and count them against each team's roster needs, so the initial rankings/roster-needs view is correct from pick 1 rather than assuming every slot is open.

### 3. Draftable Players (full player pool)

```
GET https://clickydraft.com/draftapp/leagues/{leagueId}/league-instances/{leagueInstanceId}/draftable-players
```

Returns the entire player pool for the league — both drafted and undrafted. This is the base list the custom ranking gets computed against; cross-reference with the Picks call to know who's still available.

### 4. WebSocket (real-time stream — optional)

```
wss://stream1.clickydraft.com/ws/{leagueInstanceId}
```

The stream mixes pick data in with other event types (chat, draft timer updates, pick deletions), so a filter is needed to isolate real picks. The original filtering logic (jQuery-based):

```js
var unescapedItem = $("<div>" + cometItem + "</div>").html();
var jsonItem = $.parseJSON(unescapedItem);
if (jsonItem.draftablePlayerId && jsonItem.posInRound && !jsonItem.deleteAction && !jsonItem.skipAction && (!isAuction || jsonItem.value)) {
  // this is a real pick
}
```

**Recommendation: skip the websocket.** Polling the Picks endpoint every 1–2 seconds is simpler and avoids dropped-connection handling, cross-domain certificate issues, and the extra parsing logic needed to separate real picks from chat/timer/deletion noise on the stream.

## What the tool needs to do

1. On startup (before the live draft begins): pull League Settings once (teams, roster rules) and the full Draftable Players list, then pull Picks once to read the **preloaded keeper picks** (`keeper: true`) — remove those players from the available pool and credit them against each team's roster needs immediately, so the starting state is accurate.
2. During the draft: poll the Picks endpoint every 1–2 seconds; diff against the previous poll to detect new picks (and handle `deleteAction`/`skipAction` picks correctly rather than treating them as real).
3. Recompute custom rankings on the remaining (undrafted, non-keeper) player pool using Bradley's own point-value system, mapped to this league's actual scoring settings — not generic ADP.
4. Factor in positional scarcity / roster needs (what Bradley's team still needs to fill, accounting for keepers already on his roster) alongside raw point value.
5. Surface the top recommended pick(s) live, for Bradley to act on himself. **No auto-draft / auto-submit** — this is a live recommendation display only.

## Open questions / still needed

- **Auth mechanism** — confirm via Network tab (cookie vs token) before building a standalone client outside the browser session.
- **Roster construction rules** (bench size, position slots, flex eligibility) — should be in the League Settings response; confirm exact field names against a real response.
- Confirm the preloaded-keeper picks are visible via the Picks endpoint before the draft officially opens (vs. only appearing once the draft starts) — matters for step 1 above.
- There are other calls beyond the four above that exist on the API; if a specific piece of data is needed later, it can likely be found via the Network tab or by asking directly.
- **Player projections** — the sample `draftablePlayer.projectedStats` field is `null`. The scoring engine needs per-player projected raw stats (completions, yards, TDs, etc.) to turn into fantasy points via the league's custom point values. If ClickyDraft doesn't populate `projectedStats` for this league, an external projections source (CSV import) is required — see `README.md`.

## Next steps

1. Capture one real League Settings response and one real Picks response for league 305751 / instance 305775 (via the Network tab) to confirm field names for roster rules in the ClickyDraft payload, confirm the auth headers being sent, and check whether preloaded keeper picks already show up on the Picks endpoint.
2. Move this file into the Claude Code project as the seed context. (Done — this file.)
3. Build order: API client (settings + picks + players) → startup keeper ingestion → polling/diff loop → ranking engine using the scoring table above → live recommendation output (console/dashboard). No auto-submit.
