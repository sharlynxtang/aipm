"""Feishu custom group bot webhook transport."""

from __future__ import annotations

import json
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def webhook_url(token: str) -> str:
    # Keep proxy-backed placeholders intact; the fixed hostname prevents host injection.
    if not token or any(char in token for char in "/?#") or any(ord(char) <= 32 for char in token):
        raise ValueError("FEISHU_WEBHOOK_TOKEN must be the token after /hook/ in the webhook URL")
    return f"https://open.feishu.cn/open-apis/bot/v2/hook/{token}"


def card_payload(report: str) -> dict:
    return {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": "每日 AI 情报"}},
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": report}}],
        },
    }


def send_card(url: str, report: str) -> None:
    payload = json.dumps(card_payload(report), ensure_ascii=False).encode("utf-8")
    request = Request(url, data=payload, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    with build_opener(_NoRedirect).open(request, timeout=15) as response:
        body = response.read(100_000)
    result = json.loads(body)
    if not isinstance(result, dict) or result.get("code", result.get("StatusCode")) != 0:
        raise RuntimeError(f"Feishu rejected the message: {result.get('msg', result.get('StatusMessage', 'unknown error'))}")
