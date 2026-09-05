"""One-off reconnaissance script — NOT part of the live-draft tool itself.

Run this once against a real ClickyDraft session to confirm:
  1. The captured auth actually works (vs. a 401/403 meaning it's expired
     or the wrong header entirely — see API_NOTES.md "Authentication").
  2. The real field names for roster construction / scoring settings in
     the League Settings response, so roster.py can be updated to read
     them instead of the hard-coded DEFAULT_STARTER_SLOTS guess.
  3. Whether preloaded keeper picks (`keeper: true`) are already present
     on the Picks endpoint before the live draft opens.

Usage:
    export CLICKYDRAFT_COOKIE='paste the full Cookie header value here'
    python scripts/inspect_api.py --league-id 305751 --instance-id 305775

Writes settings.json / picks.json / players_sample.json into --out-dir
(default: ./api_dump) and prints a summary to the console.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from clickydraft_assistant.api_client import ClickyDraftAPIError, ClickyDraftAuthError, ClickyDraftClient  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--league-id", type=int, default=305751)
    parser.add_argument("--instance-id", type=int, default=305775)
    parser.add_argument("--cookie-env-var", default="CLICKYDRAFT_COOKIE")
    parser.add_argument("--out-dir", default="api_dump")
    args = parser.parse_args()

    cookie = os.environ.get(args.cookie_env_var)
    if not cookie:
        print(f"No cookie found in ${args.cookie_env_var}. Export it first (see script docstring).")
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = ClickyDraftClient(league_id=args.league_id, league_instance_id=args.instance_id, cookie=cookie)

    print(f"GET league settings for league={args.league_id} instance={args.instance_id} ...")
    try:
        settings = client.get_league_settings()
    except ClickyDraftAuthError as exc:
        print(f"AUTH FAILED: {exc}")
        print("-> The cookie is missing, wrong, or expired. Re-capture it from DevTools -> Network.")
        sys.exit(1)
    except ClickyDraftAPIError as exc:
        print(f"REQUEST FAILED: {exc}")
        sys.exit(1)

    (out_dir / "settings.json").write_text(json.dumps(settings, indent=2))
    print(f"OK. Wrote {out_dir / 'settings.json'}")
    print("Top-level keys in League Settings response:")
    for key in sorted(settings.keys()):
        print(f"  - {key}")
    print()
    print("Look through settings.json for roster construction fields (bench size,")
    print("position slots, flex eligibility) and paste the relevant section back")
    print("so roster.py can be updated to read real field names instead of the")
    print("hard-coded DEFAULT_STARTER_SLOTS guess in API_NOTES.md.")
    print()

    print("GET picks ...")
    picks = client.get_picks()
    (out_dir / "picks.json").write_text(json.dumps(picks, indent=2))
    keeper_count = sum(1 for p in picks if p.get("keeper"))
    real_count = sum(1 for p in picks if not p.get("deleteAction") and not p.get("skipAction"))
    print(f"OK. Wrote {out_dir / 'picks.json'} ({len(picks)} total, {real_count} real, {keeper_count} keeper)")
    if keeper_count:
        print("-> Confirms preloaded keeper picks ARE visible on this endpoint pre-draft. Good.")
    else:
        print("-> No keeper picks seen yet. If this is a keeper league and keepers haven't")
        print("   locked in yet, re-run this closer to draft day to confirm they appear.")
    print()

    print("GET draftable-players (sample only) ...")
    players = client.get_draftable_players()
    (out_dir / "players_sample.json").write_text(json.dumps(players[:5], indent=2))
    print(f"OK. {len(players)} players total. Wrote first 5 to {out_dir / 'players_sample.json'}")
    if players:
        sample = players[0]
        has_projections = bool(sample.get("projectedStats"))
        print(f"-> Sample player projectedStats populated: {has_projections}")
        if not has_projections:
            print("   (expected to be null per API_NOTES.md — CSV projections fallback still needed)")


if __name__ == "__main__":
    main()
