"""Poll League Settings + Picks rapidly and print any JSON field that
changes between polls — a one-off recon aid for finding where ClickyDraft
exposes "seconds remaining on the current pick" (see draft_timer.py and
API_NOTES.md's open item on this).

Rationale: manually diffing two JSON blobs by eye while also watching a
countdown timer in the browser is error-prone. This script does the
diffing for you — run it while it's YOUR turn and the clock is visibly
ticking down in the ClickyDraft UI, and it'll print exactly which
field(s) changed between polls. A field that changes roughly once per
second and trends toward zero is almost certainly the timer.

This does NOT touch the websocket — if nothing here changes while your
clock ticks, the timer likely only lives there, which would need a
browser-based capture instead (DevTools -> Network -> WS -> Messages).

Usage:
    export CLICKYDRAFT_COOKIE='paste the full Cookie header value here'
    python scripts/watch_for_timer_field.py --league-id 305751 --instance-id 305775

Run it, then go make sure it's about to be your turn in the draft and
watch the console while your clock counts down. Ctrl+C to stop.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from clickydraft_assistant.api_client import ClickyDraftAPIError, ClickyDraftAuthError, ClickyDraftClient  # noqa: E402


def _flatten(obj, prefix=""):
    """Yield (path, value) for every leaf value in a nested dict/list."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _flatten(value, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from _flatten(value, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def _diff(before: dict, after: dict) -> list[tuple[str, object, object]]:
    before_flat = dict(_flatten(before))
    after_flat = dict(_flatten(after))
    changes = []
    for path in after_flat.keys() | before_flat.keys():
        b, a = before_flat.get(path), after_flat.get(path)
        if b != a:
            changes.append((path, b, a))
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--league-id", type=int, default=305751)
    parser.add_argument("--instance-id", type=int, default=305775)
    parser.add_argument("--cookie-env-var", default="CLICKYDRAFT_COOKIE")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between polls (default: 1.0)")
    args = parser.parse_args()

    cookie = os.environ.get(args.cookie_env_var)
    if not cookie:
        print(f"No cookie found in ${args.cookie_env_var}. Export it first (see script docstring).")
        sys.exit(1)

    client = ClickyDraftClient(league_id=args.league_id, league_instance_id=args.instance_id, cookie=cookie)

    print("Polling League Settings + Picks every", args.interval, "second(s). Ctrl+C to stop.")
    print("Go make it your turn in the draft and watch here while your clock counts down.\n")

    prev_settings = None
    prev_picks = None
    try:
        while True:
            try:
                settings = client.get_league_settings()
                picks = client.get_picks()
            except ClickyDraftAuthError as exc:
                print(f"AUTH FAILED: {exc}")
                sys.exit(1)
            except ClickyDraftAPIError as exc:
                print(f"Request failed, retrying: {exc}")
                time.sleep(args.interval)
                continue

            if prev_settings is not None:
                for path, before, after in _diff(prev_settings, settings):
                    print(f"[settings changed] {path}: {before!r} -> {after!r}")
            if prev_picks is not None:
                for path, before, after in _diff({"picks": prev_picks}, {"picks": picks}):
                    print(f"[picks changed]    {path}: {before!r} -> {after!r}")

            prev_settings, prev_picks = settings, picks
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
