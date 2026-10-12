"""每日入口: 采集 -> 生成 HTML -> (可选) 发送邮件

用法:
  python run_daily.py                          # 在线采集并生成报告
  python run_daily.py --from-data data/sample_20261012.json   # 用已有数据离线生成(演示/内网)
  python run_daily.py --send-email             # 采集 + 生成 + 发送邮件
  python run_daily.py --date 2026-10-12 --output output
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.config import load_config          # noqa: E402
from src.models import NewsItem             # noqa: E402
from src.collectors import collect_all      # noqa: E402
from src.report.generator import generate   # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("run_daily")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_from_json(path: str) -> tuple[list[NewsItem], list[str], list[str], str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = [NewsItem.from_dict(d) for d in data.get("items", [])]
    return items, data.get("highlights", []), data.get("intranet_guide", []), data.get("date", "")


def save_raw(items: list[NewsItem], date_str: str) -> str:
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"raw_{date_str.replace('-', '')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": date_str,
                   "items": [i.to_dict() for i in items]}, f, ensure_ascii=False, indent=2)
    return path


def sync_pages(html_path: str) -> str:
    """把报告同步到 docs/(GitHub Pages 源目录):
    - docs/index.html = 最新一期
    - docs/知识库前沿新闻推送_YYYYMMDD.html = 每日存档
    - docs/assets/ = 本地化图片(相对路径引用, 天然适配 Pages)
    - docs/archive.html = 存档索引页
    """
    docs = os.path.join(BASE_DIR, "docs")
    os.makedirs(docs, exist_ok=True)

    src_assets = os.path.join(os.path.dirname(html_path), "assets")
    if os.path.isdir(src_assets):
        shutil.copytree(src_assets, os.path.join(docs, "assets"), dirs_exist_ok=True)

    shutil.copy(html_path, os.path.join(docs, os.path.basename(html_path)))
    shutil.copy(html_path, os.path.join(docs, "index.html"))

    reports = sorted((f for f in os.listdir(docs)
                      if f.startswith("知识库前沿新闻推送_") and f.endswith(".html")),
                     reverse=True)
    lis = "\n".join(
        f'<li><a href="{f}">{f.replace("知识库前沿新闻推送_", "").replace(".html", "")}</a></li>'
        for f in reports)
    with open(os.path.join(docs, "archive.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>知识库前沿新闻推送 · 存档</title></head>
<body style="font-family:'PingFang SC','Microsoft YaHei',sans-serif;max-width:640px;margin:40px auto;padding:0 16px;color:#1f2937;">
<h1 style="font-size:22px;">📚 知识库前沿新闻推送 · 存档</h1>
<p style="color:#6b7280;font-size:13px;">最新一期请直接访问 <a href="index.html">首页</a></p>
<ul style="line-height:2;">{lis}</ul>
</body></html>""")
    return docs


def pipeline(from_data: str | None = None, send_email: bool = False,
             pages: bool = False, date_str: str | None = None,
             config_path: str = "config.yaml", output: str | None = None) -> str:
    """完整流水线: 采集(或离线数据) -> 生成报告 -> (可选)Pages -> (可选)邮件。
    供 CLI 和定时调度器(scheduler.py)共用。返回报告路径。"""
    cfg = load_config(config_path)
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")

    if from_data:
        log.info("离线模式: 从 %s 读取数据", from_data)
        items, highlights, guide, d = load_from_json(from_data)
        date_str = d or date_str
    else:
        log.info("在线采集模式")
        items = collect_all(cfg)
        highlights, guide = [], []
        raw = save_raw(items, date_str)
        log.info("原始数据已保存: %s (%d 条)", raw, len(items))

    if not items:
        raise RuntimeError("没有任何条目,报告未生成。请检查网络/代理或数据源配置。")

    out_dir = output or os.path.join(BASE_DIR, cfg.get("report", {}).get("output_dir", "output"))
    html_path = generate(items, cfg, highlights=highlights, intranet_guide=guide,
                         date_str=date_str, out_dir=out_dir)
    log.info("报告已生成: %s", html_path)

    if pages:
        log.info("GitHub Pages 目录已更新: %s", sync_pages(html_path))

    if send_email:
        from src.mailer import send_report
        send_report(html_path, cfg, date_str,
                    items=items, highlights=highlights, intranet_guide=guide)
        log.info("邮件已发送")

    return html_path


def main() -> None:
    ap = argparse.ArgumentParser(description="知识库前沿新闻推送")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--from-data", help="跳过采集,用指定 JSON 数据生成报告")
    ap.add_argument("--send-email", action="store_true", help="生成后发送邮件")
    ap.add_argument("--pages", action="store_true", help="同步报告到 docs/(GitHub Pages 源目录)")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--output", default=None, help="输出目录(默认 config 中 report.output_dir)")
    args = ap.parse_args()

    try:
        html_path = pipeline(from_data=args.from_data, send_email=args.send_email,
                             pages=args.pages, date_str=args.date,
                             config_path=args.config, output=args.output)
    except RuntimeError as e:
        log.error("%s", e)
        sys.exit(1)
    print(f"\n✅ 完成: {html_path}")


if __name__ == "__main__":
    main()
