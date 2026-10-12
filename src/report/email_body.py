"""邮件正文生成 —— 内网手机端友好版

设计原则(针对企业内网手机邮件客户端):
- 全部样式内联: 多数邮件客户端(尤其手机端/Outlook)会剥离 <style> 标签
- 零外部资源: 不引用任何图片/字体/CDN, 离线可完整阅读
- 内容自足: 标题/摘要/效果/复现性全部内联, 不点开链接也能读完
- 链接兜底: URL 以纯文本完整展示, 客户端禁用超链接时可长按复制
"""
from __future__ import annotations

from html import escape

from ..models import NewsItem, CATEGORY_NAMES, CATEGORY_ORDER

_REPRO_COLOR = {"高": "#16a34a", "中": "#d97706", "低": "#dc2626"}


def _item_block(it: NewsItem, full: bool) -> str:
    """full=True(GitHub 卡片)时附带要点/效果/复现; 否则仅标题+摘要。"""
    meta_parts = [escape(it.source)]
    if it.published:
        meta_parts.append(escape(it.published))
    if it.heat:
        meta_parts.append(escape(it.heat))
    meta = " · ".join(meta_parts)

    html = [
        '<div style="padding:14px 18px;border-bottom:1px solid #e5e7eb;">',
        f'<div style="font-size:11px;color:#9ca3af;margin-bottom:3px;">{meta}</div>',
        f'<div style="font-size:15px;font-weight:700;line-height:1.5;color:#1f2937;">{escape(it.title)}</div>',
    ]
    if it.summary:
        html.append(
            f'<div style="font-size:13px;color:#4b5563;line-height:1.65;margin-top:4px;">{escape(it.summary)}</div>')
    if full and it.key_points:
        for kp in it.key_points[:3]:
            html.append(
                f'<div style="font-size:12.5px;color:#374151;line-height:1.6;margin-top:2px;">'
                f'<span style="color:#4f46e5;">▸</span> {escape(kp)}</div>')
    if full and it.effect:
        html.append(
            f'<div style="font-size:12.5px;color:#166534;background:#f0fdf4;border-left:3px solid #16a34a;'
            f'padding:6px 10px;margin-top:8px;line-height:1.6;"><b>⚡ 效果</b> ｜ {escape(it.effect)}</div>')
    if full and it.repro_level:
        color = _REPRO_COLOR.get(it.repro_level, "#6b7280")
        html.append(
            f'<div style="font-size:12px;color:#6b7280;margin-top:8px;line-height:1.6;">'
            f'<span style="color:#ffffff;background:{color};padding:1px 7px;border-radius:4px;'
            f'font-weight:700;">内网复现·{escape(it.repro_level)}</span> {escape(it.repro_note)}</div>')
    if it.url:
        u = escape(it.url)
        html.append(
            f'<div style="font-size:11.5px;margin-top:8px;word-break:break-all;">'
            f'🔗 <a href="{u}" style="color:#4f46e5;text-decoration:none;">{u}</a></div>')
    html.append('</div>')
    return "".join(html)


def build_html(title: str, date_str: str, items: list[NewsItem],
               highlights: list[str], intranet_guide: list[str]) -> str:
    parts: list[str] = [
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">',
        f'<title>{escape(title)} · {escape(date_str)}</title></head>',
        '<body style="margin:0;padding:0;background:#f4f5f7;">',
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#f4f5f7"><tr><td align="center" style="padding:16px 8px;">',
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;">',

        # 头部
        '<tr><td style="background:#4f46e5;background:linear-gradient(135deg,#312e81,#7c3aed);'
        'border-radius:12px 12px 0 0;padding:22px 24px;">',
        f'<div style="font-size:11px;color:#c7d2fe;letter-spacing:2px;">KNOWLEDGE BASE × AGENT · FRONTIER DAILY</div>',
        f'<div style="font-size:22px;font-weight:700;color:#ffffff;margin-top:6px;">{escape(title)}</div>',
        f'<div style="font-size:12.5px;color:#e0e7ff;margin-top:6px;">📅 {escape(date_str)} ・ 共 {len(items)} 条 ・ 全部内容内联可读,无需点击链接</div>',
        '</td></tr>',
    ]

    # 今日摘要
    if highlights:
        parts.append('<tr><td style="background:#ffffff;padding:18px 24px;border-bottom:1px solid #e5e7eb;">'
                     '<div style="font-size:15px;font-weight:700;color:#4f46e5;margin-bottom:8px;">📌 今日摘要</div>')
        for i, h in enumerate(highlights, 1):
            parts.append(f'<div style="font-size:13px;color:#374151;line-height:1.7;margin:5px 0;">'
                         f'<b style="color:#4f46e5;">{i}.</b> {escape(h)}</div>')
        parts.append('</td></tr>')

    # 正文区块
    for cat in CATEGORY_ORDER:
        cat_items = [i for i in items if i.category == cat]
        if not cat_items:
            continue
        dot = {"github": "#24292f", "domestic": "#c2410c", "international": "#0369a1"}[cat]
        parts.append(
            f'<tr><td style="background:#ffffff;padding:14px 18px 4px;border-top:6px solid #f4f5f7;">'
            f'<span style="display:inline-block;width:9px;height:9px;background:{dot};border-radius:2px;margin-right:8px;"></span>'
            f'<span style="font-size:16px;font-weight:700;color:#1f2937;">{escape(CATEGORY_NAMES[cat])}</span>'
            f'<span style="font-size:12px;color:#9ca3af;margin-left:8px;">{len(cat_items)} 条</span>'
            f'</td></tr>')
        blocks = "".join(_item_block(it, full=(cat == "github")) for it in cat_items)
        parts.append(f'<tr><td style="background:#ffffff;padding:0;">{blocks}</td></tr>')

    # 内网指南
    if intranet_guide:
        parts.append('<tr><td style="background:#ffffff;border-top:6px solid #f4f5f7;padding:16px 24px;">'
                     '<div style="font-size:15px;font-weight:700;color:#1f2937;margin-bottom:8px;">🖥 内网可复现性说明</div>')
        for g in intranet_guide:
            parts.append(f'<div style="font-size:12.5px;color:#4b5563;line-height:1.7;margin:4px 0;">• {escape(g)}</div>')
        parts.append('</td></tr>')

    # 页脚
    parts.append(
        '<tr><td style="background:#ffffff;border-radius:0 0 12px 12px;border-top:1px solid #e5e7eb;'
        'padding:14px 24px;font-size:11px;color:#9ca3af;line-height:1.7;">'
        '本邮件由 KB-Ontology-News 自动生成 ・ 完整图文版报告见附件 HTML(电脑端打开体验更佳)<br>'
        '若链接不可点击,请长按复制链接到浏览器打开 ・ 热度数据为采集时刻快照'
        '</td></tr>')

    parts.append('</table></td></tr></table></body></html>')
    return "".join(parts)


def build_text(title: str, date_str: str, items: list[NewsItem],
               highlights: list[str], intranet_guide: list[str]) -> str:
    """纯文本版: 客户端禁用 HTML 时的兜底, 同样内容自足。"""
    lines = [f"{title} · {date_str}", "=" * 46, ""]
    if highlights:
        lines.append("【今日摘要】")
        for i, h in enumerate(highlights, 1):
            lines.append(f"{i}. {h}")
        lines.append("")
    for cat in CATEGORY_ORDER:
        cat_items = [i for i in items if i.category == cat]
        if not cat_items:
            continue
        lines.append(f"■ {CATEGORY_NAMES[cat]}({len(cat_items)} 条)")
        lines.append("-" * 46)
        for it in cat_items:
            meta = " · ".join(p for p in (it.source, it.published, it.heat) if p)
            lines.append(f"◆ {it.title}")
            lines.append(f"  [{meta}]")
            if it.summary:
                lines.append(f"  {it.summary}")
            if cat == "github":
                for kp in it.key_points[:3]:
                    lines.append(f"  - {kp}")
                if it.effect:
                    lines.append(f"  效果: {it.effect}")
                if it.repro_level:
                    lines.append(f"  内网复现·{it.repro_level}: {it.repro_note}")
            lines.append(f"  链接: {it.url}")
            lines.append("")
    if intranet_guide:
        lines.append("【内网可复现性说明】")
        for g in intranet_guide:
            lines.append(f"• {g}")
        lines.append("")
    lines.append("—— KB-Ontology-News 自动生成;完整图文版见邮件附件")
    return "\n".join(lines)
