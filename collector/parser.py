from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


class FeedParseError(Exception):
    """Raised when feed payload cannot be parsed as RSS/Atom."""


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _find_descendant_text(node: ET.Element, names: set[str]) -> str | None:
    for child in node.iter():
        if _local_name(child.tag) in names:
            text = _text_or_none(child.text)
            if text:
                return text
    return None


def _extract_link(node: ET.Element) -> str | None:
    for child in node.iter():
        if _local_name(child.tag) != "link":
            continue
        text = _text_or_none(child.text)
        if text and text.startswith(("http://", "https://")):
            return text
        href = _text_or_none(child.attrib.get("href"))
        rel = _text_or_none(child.attrib.get("rel")) or "alternate"
        if href and rel in {"alternate", "self"}:
            return href
    return None


def _extract_source(node: ET.Element) -> tuple[str | None, str | None]:
    source_name = None
    source_url = None
    for child in node.iter():
        name = _local_name(child.tag)
        if name == "source":
            source_name = source_name or _text_or_none(child.text)
            source_url = source_url or _text_or_none(child.attrib.get("url"))
        if name == "creator" and source_name is None:
            source_name = _text_or_none(child.text)
        if name == "uri" and source_url is None:
            source_url = _text_or_none(child.text)
        if name == "title" and _local_name(node.tag) == "source" and source_name is None:
            source_name = _text_or_none(child.text)
    return source_name, source_url


def _domain_from_link(link: str | None) -> str | None:
    if not link:
        return None
    parsed = urlparse(link)
    return _text_or_none(parsed.netloc)


def _item_ref(node: ET.Element, link: str | None) -> str:
    ref = (
        _find_descendant_text(node, {"guid", "id"})
        or link
        or _find_descendant_text(node, {"title"})
        or "unknown_item"
    )
    return ref[:200]


@dataclass
class ParsedItem:
    title: str | None
    link: str | None
    snippet: str | None
    source_name: str | None
    source_url: str | None
    published_at: str | None
    payload: dict[str, Any]
    item_ref: str


def parse_feed(xml_payload: bytes) -> list[ParsedItem]:
    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError as exc:
        raise FeedParseError(f"XML parse error: {exc}") from exc

    root_name = _local_name(root.tag).lower()
    items: list[ET.Element]
    if root_name == "rss":
        channel = next((c for c in root if _local_name(c.tag).lower() == "channel"), None)
        if channel is None:
            raise FeedParseError("RSS channel not found")
        items = [c for c in channel if _local_name(c.tag).lower() == "item"]
    elif root_name in {"feed"}:
        items = [c for c in root if _local_name(c.tag).lower() == "entry"]
    elif root_name == "rdf":
        items = [c for c in root if _local_name(c.tag).lower() == "item"]
    else:
        raise FeedParseError(f"Unsupported feed root: {root_name}")

    parsed: list[ParsedItem] = []
    for node in items:
        link = _extract_link(node)
        source_name, source_url = _extract_source(node)
        snippet = _find_descendant_text(node, {"description", "summary", "content"})
        title = _find_descendant_text(node, {"title"})
        published_at = _find_descendant_text(node, {"pubDate", "published", "updated"})
        source_name = source_name or _domain_from_link(link)
        source_url = source_url or link

        payload = {
            "raw_xml": ET.tostring(node, encoding="unicode"),
            "title": title,
            "link": link,
            "snippet": snippet,
            "source_name": source_name,
            "source_url": source_url,
            "published_at": published_at,
        }
        parsed.append(
            ParsedItem(
                title=title,
                link=link,
                snippet=snippet,
                source_name=source_name,
                source_url=source_url,
                published_at=published_at,
                payload=payload,
                item_ref=_item_ref(node, link),
            )
        )
    return parsed

