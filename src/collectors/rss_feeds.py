"""RSS/Atom 通用采集器(纯 stdlib 解析): 覆盖国内外论坛资讯"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from ..models import NewsItem
from .base import http_get, clean_html

log = logging.getLogger(__name__)

ATOM = "{http://www.w3.org/2005/Atom}"


def _parse_date(rss_date: str, atom_date: str) -> str:
    for raw in (rss_date, atom_date):
        if not raw:
            continue
        try:
            return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            pass
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def _within_days(date_str: str, days: int) -> bool:
    if not date_str:
        return True  # 无日期的源不过滤
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return dt >= datetime.now(timezone.utc) - timedelta(days=days)


def _match_keywords(text: str, keywords: list[str]) -> list[str]:
    low = text.lower()
    return [k for k in keywords if k.lower() in low]


def _parse_feed(xml_text: str) -> list[dict]:
    """同时兼容 RSS2.0 与 Atom,返回统一的 dict 列表。"""
    root = ET.fromstring(xml_text)
    entries = []
    if root.tag == f"{ATOM}feed":
        for e in root.findall(f"{ATOM}entry"):
            link = ""
            for l in e.findall(f"{ATOM}link"):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
                    break
            entries.append({
                "title": e.findtext(f"{ATOM}title") or "",
                "link": link,
                "date": _parse_date("", e.findtext(f"{ATOM}published") or e.findtext(f"{ATOM}updated") or ""),
                "desc": e.findtext(f"{ATOM}summary") or e.findtext(f"{ATOM}content") or "",
            })
    else:
        for item in root.iter("item"):
            entries.append({
                "title": item.findtext("title") or "",
                "link": item.findtext("link") or "",
                "date": _parse_date(item.findtext("pubDate") or "", ""),
                "desc": item.findtext("description") or "",
            })
    return entries


def collect(cfg: dict) -> list[NewsItem]:
    keywords = cfg.get("keywords", [])
    days = cfg.get("rss_days", 7)  # RSS 收录窗口(天)
    items: list[NewsItem] = []
    for feed in cfg.get("rss_feeds", []):
        if not feed.get("enabled", True):
            continue
        name = feed.get("name", feed.get("url"))
        try:
            entries = _parse_feed(http_get(feed["url"], cfg).text)
        except Exception as e:
            log.warning("RSS 源 %s 不可用,已跳过: %s", name, e)
            continue
        hit = 0
        for e in entries:
            text = f"{e['title']} {clean_html(e['desc'])}"
            matched = _match_keywords(text, keywords)
            if not matched or not _within_days(e["date"], days):
                continue
            items.append(NewsItem(
                title=e["title"].strip(),
                url=e["link"].strip(),
                source=name,
                category=feed.get("category", "domestic"),
                published=e["date"],
                summary=clean_html(e["desc"])[:200],
                tags=matched[:4],
            ))
            hit += 1
            if hit >= 5:
                break
        log.info("RSS 源 %s: 命中 %d 条", name, hit)
    return items
