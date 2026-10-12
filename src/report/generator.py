"""HTML 报告生成"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models import NewsItem, CATEGORY_NAMES, CATEGORY_ORDER
from ..collectors.base import http_get

log = logging.getLogger(__name__)

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def _localize_images(items: list[NewsItem], out_dir: str, cfg: dict) -> None:
    """把远程图片下载到 out_dir/assets, 改写成相对路径 —— 内网打开 HTML 也能看图。"""
    assets = os.path.join(out_dir, "assets")
    os.makedirs(assets, exist_ok=True)
    for it in items:
        url = it.image_url
        if not url or not url.startswith("http"):
            continue
        ext = ".png"
        fname = hashlib.md5(url.encode()).hexdigest()[:12] + ext
        fpath = os.path.join(assets, fname)
        if not os.path.exists(fpath):
            try:
                resp = http_get(url, cfg)
                with open(fpath, "wb") as f:
                    f.write(resp.content)
            except Exception as e:
                log.warning("图片下载失败,保留远程链接 %s: %s", url, e)
                continue
        it.image_url = f"assets/{fname}"


def auto_highlights(items: list[NewsItem], limit: int = 5) -> list[str]:
    """无人工精选时的兜底摘要: 取每个分类前几条的一句话概括。
    后续可在此接入内网 LLM 端点生成真正的编辑级摘要。"""
    highlights = []
    for it in items:
        first = (it.summary or it.title).split("。")[0].strip()
        if first:
            highlights.append(f"{it.title} —— {first}")
        if len(highlights) >= limit:
            break
    return highlights


def generate(items: list[NewsItem], cfg: dict,
             highlights: list[str] | None = None,
             intranet_guide: list[str] | None = None,
             date_str: str | None = None,
             out_dir: str | None = None) -> str:
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    out_dir = out_dir or cfg.get("report", {}).get("output_dir", "output")
    os.makedirs(out_dir, exist_ok=True)

    if cfg.get("report", {}).get("localize_images"):
        _localize_images(items, out_dir, cfg)

    max_per = cfg.get("report", {}).get("max_items_per_section", 10)
    sections = []
    for cat in CATEGORY_ORDER:
        cat_items = [i for i in items if i.category == cat][:max_per]
        if cat_items:
            sections.append({"key": cat, "name": CATEGORY_NAMES[cat], "items": cat_items})

    stats = {
        "total": sum(len(s["items"]) for s in sections),
        "github": sum(len(s["items"]) for s in sections if s["key"] == "github"),
        "domestic": sum(len(s["items"]) for s in sections if s["key"] == "domestic"),
        "international": sum(len(s["items"]) for s in sections if s["key"] == "international"),
    }

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
    env.filters["first"] = lambda s, n=1: (s or "")[:n]
    tpl = env.get_template("report.html.j2")
    html = tpl.render(
        title=cfg.get("report", {}).get("title", "知识库与本体论 · AI 进展日报"),
        date_str=date_str,
        issue=date_str.replace("-", ""),
        sections=sections,
        stats=stats,
        highlights=highlights or auto_highlights(items),
        intranet_guide=intranet_guide or [],
    )

    out_path = os.path.join(out_dir, f"知识库前沿新闻推送_{date_str.replace('-', '')}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("报告已生成: %s", out_path)
    return out_path
