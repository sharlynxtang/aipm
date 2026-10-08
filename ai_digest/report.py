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
    ("release", "GLOBAL"): "开源生态发布",
    ("official", "GLOBAL"): "官方资讯",
    ("paper", "GLOBAL"): "论文",
    ("podcast", "GLOBAL"): "播客",
    ("conference", "GLOBAL"): "会议动态",
}


def _safe(value: str) -> str:
    return re.sub(r"([\\`*_\[\]()])", r"\\\1", value).replace("\n", " ")


def render_report(items: list[Item], now: datetime, succeeded: int, total: int, failed: list[str], require_summaries: bool = False) -> str:
    if require_summaries and any(not item.chinese_summary for item in items):
        raise ValueError("every selected item needs a Chinese summary before delivery")
    date = now.astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
    note = "中文摘要依据来源标题与订阅摘录生成；请点原文核查。" if require_summaries else "预览显示来源摘录；发送时生成逐条中文摘要。"
    lines = [f"**每日 AI 情报｜{date}**", f"面向开源模型产品经理与战略经理；{note}"]

    counts = Counter(signal for item in items for signal in item.signals)
    if counts:
        lines.append("**今日信号（按入选条目计数）：**")
        for name, count in counts.most_common(3):
            evidence = max((item for item in items if name in item.signals), key=lambda item: (item.score, item.published))
            lines.append(f"• {_safe(name)} {count} 条 · [{_safe(evidence.title)}]({evidence.url})")

    product_candidates = [item for item in items if any(s in item.signals for s in ("产品与智能体", "成本与部署"))]
    if not product_candidates:
        product_candidates = [item for item in items if "评测与训练" in item.signals]
    product_candidates = [item for item in product_candidates if item.source.category in {"news", "official", "release"}] or product_candidates
    product = max(product_candidates, key=lambda item: (item.score, item.published), default=None)
    strategy_candidates = [item for item in items if item != product and any(s in item.signals for s in ("开源与生态", "竞争与政策"))]
    strategy_candidates = [item for item in strategy_candidates if item.source.category in {"news", "official", "release"}] or strategy_candidates
    strategy = max(strategy_candidates, key=lambda item: (item.score, item.published), default=None)
    if not strategy:
        strategy = next((item for item in items if any(s in item.signals for s in ("开源与生态", "竞争与政策"))), None)
    if product:
        action = "核对延迟、吞吐与部署成本" if "成本与部署" in product.signals else "验证目标场景与集成门槛"
        lines.append(f"**产品关注：**[{_safe(product.title)}]({product.url})｜待验证：{action}。")
    if strategy:
        if strategy.source.category == "release":
            action = "核对版本变更、兼容性与生态影响"
        else:
            action = "核对许可证、社区采用与生态兼容性" if "开源与生态" in strategy.signals else "跟踪竞品位置与政策影响"
        lines.append(f"**战略关注：**[{_safe(strategy.title)}]({strategy.url})｜待验证：{action}。")
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
            if item.chinese_summary:
                lines.append(f"  摘要：{_safe(item.chinese_summary)}")
            elif item.summary and not require_summaries:
                lines.append(f"  来源摘录：{_safe(item.summary[:140])}")

    lines.append(f"\n来源抓取：{succeeded}/{total} 成功。")
    if failed:
        lines.append("未抓取：" + "、".join(_safe(name) for name in failed) + "。本期内容可能不完整。")
    return "\n".join(lines)
