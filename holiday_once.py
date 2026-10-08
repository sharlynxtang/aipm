"""One-time, reviewed October 1-7 briefing; this file is absent from main."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ai_digest.feishu import send_card, webhook_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate the prepared briefing without sending")
    parser.add_argument("--send", action="store_true", help="Send the prepared briefing to Feishu")
    args = parser.parse_args()
    if args.check == args.send:
        parser.error("choose exactly one of --check or --send")
    report = Path(__file__).with_name("holiday_report.md").read_text(encoding="utf-8")
    if not report.startswith("**国庆假期 AI 情报补刊") or report.count("  摘要：") != 15:
        print("Holiday briefing failed its content check.", file=sys.stderr)
        return 2
    if args.check:
        print(f"Checked 15 items; report size {len(report.encode('utf-8'))} bytes.")
        return 0
    token = os.environ.get("FEISHU_WEBHOOK_TOKEN")
    if not token:
        print("::error::FEISHU_WEBHOOK_TOKEN is missing; holiday briefing was not sent.")
        return 2
    try:
        send_card(webhook_url(token), report)
    except Exception as error:
        print(f"::error::Holiday briefing send failed ({type(error).__name__}); check Feishu bot and network.")
        return 2
    print("Sent 15-item October 1-7 holiday briefing to Feishu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
