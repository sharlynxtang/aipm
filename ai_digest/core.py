"""Collect and rank dated RSS/Atom items without fabricating source claims."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ATOM = "{http://www.w3.org/2005/Atom}"
MAX_FEED_BYTES = 2_000_000
USER_AGENT = "AIPM-Daily-Digest/0.1 (+https://github.com/sharlynxtang/aipm)"

SIGNALS = {
    "开源与生态": ("open source", "open-source", "open weight", "open-weight", "开源", "开放权重", "hugging face", "qwen", "deepseek", "llama"),
    "产品与智能体": ("agent", "agents", "assistant", "workflow", "应用", "产品", "智能体", "助手", "多模态"),
    "成本与部署": ("inference", "latency", "pricing", "cost", "deploy", "推理", "延迟", "价格", "成本", "部署", "量化"),
    "竞争与政策": ("funding", "acquisition", "regulation", "policy", "market", "融资", "收购", "监管", "政策", "市场"),
    "评测与训练": ("benchmark", "evaluation", "evals", "training", "fine-tuning", "finetuning", "基准", "评测", "训练", "微调"),
}
AI_TERMS = ("人工智能", "大模型", "生成式", "机器学习", "openai", "anthropic", "chatgpt", "llm", "agent", "deepseek", "qwen", "模型", "model", "hugging face")


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    category: str
    region: str
    url: str


@dataclass(frozen=True)
class Item:
    source: Source
    title: str
    url: str
    published: datetime
    summary: str
    signals: tuple[str, ...]
    score: int
    guid: str = ""
    chinese_summary: str = ""


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def clean_text(value: str, limit: int = 400) -> str:
    parser = _Text()
    parser.feed(value)
    plain = html.unescape(" ".join(parser.parts))
    return re.sub(r"\s+", " ", plain).strip()[:limit]


def parse_date(value: str) -> datetime | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _field(node: ET.Element, *names: str) -> str:
    for name in names:
        value = node.findtext(name)
        if value and value.strip():
            return value.strip()
    return ""


def _atom_link(node: ET.Element) -> str:
    for link in node.findall(f"{ATOM}link"):
        if link.get("rel", "alternate") == "alternate" and link.get("href"):
            return link.get("href", "")
    return ""


def classify(title: str, summary: str, category: str) -> tuple[tuple[str, ...], int]:
    title_low = title.casefold()
    text_low = f"{title} {summary}".casefold()
    matched = [label for label, keywords in SIGNALS.items() if any(word in text_low for word in keywords)]
    if category == "release" and "开源与生态" not in matched:
        matched.insert(0, "开源与生态")
    title_hits = sum(any(word in title_low for word in words) for words in SIGNALS.values())
    base = {"release": 5, "official": 4, "paper": 2, "conference": 3, "news": 1, "podcast": 2}[category]
    return tuple(matched), base + 2 * title_hits + len(matched)


def is_relevant(item: Item) -> bool:
    if item.source.category == "release":
        return not bool(re.search(r"(?i)(?:-?rc\d*|-?alpha\d*|-?beta\d*|\.dev\d*|release candidate)\b", item.title))
    if item.source.category != "news":
        return True  # These feeds have a specific AI, paper, podcast, or conference remit.
    text = f"{item.title} {item.summary}".casefold()
    return any(word in text for word in AI_TERMS) or bool(re.search(r"(?<![a-z])ai(?![a-z])", text))


def parse_feed(payload: bytes, source: Source) -> list[Item]:
    root = ET.fromstring(payload)
    if root.tag not in {"rss", f"{ATOM}feed", "{http://purl.org/rss/1.0/}RDF"}:
        raise ValueError("unsupported feed format")
    entries = root.findall("./channel/item") if root.tag == "rss" else root.findall(f"{ATOM}entry")
    if root.tag == "{http://purl.org/rss/1.0/}RDF":
        entries = root.findall("{http://purl.org/rss/1.0/}item")

    items: list[Item] = []
    for entry in entries:
        atom = entry.tag == f"{ATOM}entry"
        title = clean_text(_field(entry, f"{ATOM}title" if atom else "title"), 180)
        url = _atom_link(entry) if atom else _field(entry, "link")
        date_text = _field(entry, f"{ATOM}published", f"{ATOM}updated") if atom else _field(entry, "pubDate", "{http://purl.org/dc/elements/1.1/}date")
        summary = clean_text(_field(entry, f"{ATOM}summary", f"{ATOM}content") if atom else _field(entry, "description", "{http://purl.org/rss/1.0/modules/content/}encoded"))
        published = parse_date(date_text)
        if not title or not url.startswith("https://") or published is None:
            continue
        guid = _field(entry, f"{ATOM}id" if atom else "guid")
        signals, score = classify(title, summary, source.category)
        items.append(Item(source, title, url, published, summary, signals, score, guid))
    return items


def load_sources(path: Path) -> list[Source]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("sources.json must be a nonempty array")
    sources = [Source(**row) for row in raw]
    if len({s.id for s in sources}) != len(sources):
        raise ValueError("source IDs must be unique")
    for source in sources:
        if source.category not in {"release", "official", "paper", "conference", "news", "podcast"}:
            raise ValueError(f"invalid category: {source.category}")
        if source.region not in {"CN", "GLOBAL"} or urlsplit(source.url).scheme != "https":
            raise ValueError(f"invalid region or URL: {source.id}")
    return sources


def fetch_source(source: Source, fixture_dir: Path | None = None) -> list[Item]:
    if fixture_dir:
        payload = (fixture_dir / f"{source.id}.xml").read_bytes()
    else:
        request = Request(source.url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
        with urlopen(request, timeout=15) as response:
            payload = response.read(MAX_FEED_BYTES + 1)
        if len(payload) > MAX_FEED_BYTES:
            raise ValueError("feed exceeds 2 MB")
    return parse_feed(payload, source)


def canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    query = urlencode([(key, value) for key, value in parse_qsl(parsed.query) if not key.lower().startswith(("utm_", "ref", "fbclid"))])
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), query, ""))


def select_items(items: list[Item], now: datetime, hours: int = 48, limit: int = 10) -> list[Item]:
    now = now.astimezone(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    eligible = [item for item in items if cutoff <= item.published <= now + timedelta(minutes=5) and is_relevant(item)]
    eligible.sort(key=lambda item: (item.score, item.published), reverse=True)
    unique: list[Item] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    seen_guids: set[tuple[str, str]] = set()
    for item in eligible:
        title_key = re.sub(r"\W+", "", item.title.casefold())
        url_key = canonical_url(item.url)
        guid_key = (item.source.id, item.guid)
        if url_key in seen_urls or title_key in seen_titles or (item.guid and guid_key in seen_guids):
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        if item.guid:
            seen_guids.add(guid_key)
        unique.append(item)

    selected: list[Item] = []
    used: set[Item] = set()
    category_caps = {"news": 4, "release": 3, "official": 2, "paper": 2, "podcast": 2, "conference": 1}

    def has_room(item: Item) -> bool:
        source_cap = 1 if item.source.category == "release" else 2
        return (
            item not in used
            and len(selected) < limit
            and sum(chosen.source.id == item.source.id for chosen in selected) < source_cap
            and sum(chosen.source.category == item.source.category for chosen in selected) < category_caps[item.source.category]
        )

    # Reserve room for the kinds of evidence requested by the team.
    for predicate in (
        lambda x: x.source.category == "news" and x.source.region == "CN",
        lambda x: x.source.category == "news" and x.source.region == "GLOBAL",
        lambda x: x.source.category == "release",
        lambda x: x.source.category == "official",
        lambda x: x.source.category == "paper",
        lambda x: x.source.category == "podcast",
        lambda x: x.source.category == "conference",
    ):
        match = next((item for item in unique if predicate(item) and has_room(item)), None)
        if match:
            selected.append(match)
            used.add(match)
    for item in unique:
        if len(selected) >= limit:
            break
        if has_room(item):
            selected.append(item)
            used.add(item)
    return selected
