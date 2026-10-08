"""Daily collection and delivery command."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .core import fetch_source, load_sources, select_items
from .feishu import send_card, webhook_url
from .report import render_report


DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "sources.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect and optionally send a source-linked daily AI digest")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--fixture-dir", type=Path, help="Read <source-id>.xml fixtures instead of the network")
    parser.add_argument("--now", help="UTC/offset ISO timestamp for reproducible checks")
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--send", action="store_true", help="Send to the Feishu webhook; default prints the digest")
    args = parser.parse_args(argv)

    if args.hours < 1 or not 1 <= args.limit <= 15:
        parser.error("--hours must be positive and --limit must be between 1 and 15")
    if args.fixture_dir and args.send:
        parser.error("fixtures cannot be sent")
    try:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
        if now.tzinfo is None:
            parser.error("--now must include a timezone")
        sources = load_sources(args.config)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))

    items = []
    failed = []
    for source in sources:
        try:
            items.extend(fetch_source(source, args.fixture_dir))
        except Exception as error:  # A failed feed must not conceal successful sources.
            failed.append(source.name)
            print(f"source {source.id} failed: {error}", file=sys.stderr)
    succeeded = len(sources) - len(failed)
    if not succeeded:
        print("No sources could be fetched; no digest was sent.", file=sys.stderr)
        return 2

    selected = select_items(items, now, args.hours, args.limit)
    report = render_report(selected, now, succeeded, len(sources), failed)
    if not args.send:
        print(report)
        return 0
    token = os.environ.get("FEISHU_WEBHOOK_TOKEN")
    if not token:
        print("FEISHU_WEBHOOK_TOKEN is required for --send.", file=sys.stderr)
        return 2
    try:
        send_card(webhook_url(token), report)
    except Exception as error:
        # Transport exceptions can contain a request URL, which contains the token.
        print(f"Feishu send failed ({type(error).__name__}); check bot and network settings.", file=sys.stderr)
        return 2
    print(f"Sent {len(selected)} items to Feishu; sources {succeeded}/{len(sources)}.")
    return 0
