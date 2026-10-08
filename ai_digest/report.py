"""Render a short, source-linked briefing for Feishu."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from .core import Item


LOCAL_TZ = ZoneInfo("Asia/Shanghai")
SECTION_NAMES = {
    ("news", "CN"): "中国科技新闻",
    ("news", "GLOBAL"): "海外科技新闻",
    ("official", "GLOBAL"): "官方资讯",
    ("paper", "GLOBAL"): "论文",
    ("podcast", "GLOBAL"): "播客",
    ("conference", "GLOBAL"): "会议动态",
}


def _safe(value: str) -> str:
    return re.sub(r"([\\`*_\[\]()])", r"\\\1", value).replace("\n", " ")


def render_report(items: list[Item], now: datetime, succeeded: int, total: int, failed: list[str]) -> str:
    date = now.astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
    lines = [f"**每日 AI 情报｜{date}**", "面向开源模型产品经理与战略经理；摘要只依据来源原文。"]

    counts = Counter(signal for item in items for signal in item.signals)
    if counts:
        signals = "、".join(f"{_safe(name)} {count}" for name, count in counts.most_common(3))
        lines.append(f"**今日信号：**{signals}（按入选条目计数）")

    product = next((item for item in items if any(s in item.signals for s in ("产品与智能体", "成本与部署", "模型与评测"))), None)
    strategy = next((item for item in items if item != product and any(s in item.signals for s in ("开源与生态", "竞争与政策"))), None)
    if not strategy:
        strategy = next((item for item in items if any(s in item.signals for s in ("开源与生态", "竞争与政策"))), None)
    if product:
        lines.append(f"**产品关注：**[{_safe(product.title)}]({product.url})｜建议核查用户场景、集成门槛与成本。")
    if strategy:
        lines.append(f"**战略关注：**[{_safe(strategy.title)}]({strategy.url})｜建议核查开放程度、竞争影响与生态机会。")
    if not items:
        lines.append("本次时间窗口内没有符合条件的新条目。")

    for (category, region), label in SECTION_NAMES.items():
        section = [item for item in items if item.source.category == category and item.source.region == region]
        if not section:
            continue
        lines.append(f"\n**{label}**")
        for item in section:
            published = item.published.astimezone(LOCAL_TZ).strftime("%m-%d %H:%M")
            lines.append(f"• [{_safe(item.title)}]({item.url}) · {_safe(item.source.name)} · {published}")
            if item.summary:
                lines.append(f"  {_safe(item.summary[:140])}")

    lines.append(f"\n来源抓取：{succeeded}/{total} 成功。")
    if failed:
        lines.append("未抓取：" + "、".join(_safe(name) for name in failed) + "。本期内容可能不完整。")
    return "\n".join(lines)
