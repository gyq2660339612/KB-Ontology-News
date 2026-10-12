"""SMTP 邮件发送

邮件结构: multipart/mixed
└── multipart/alternative
│   ├── text/plain   纯文本兜底(客户端禁用 HTML 时)
│   └── text/html    手机端友好版(内联样式/零外部资源/纯文本链接)
└── 附件: 完整图文版 HTML 报告(电脑端打开)
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from .models import NewsItem  # noqa: F401  (仅用于类型标注)
from .report.email_body import build_html, build_text

log = logging.getLogger(__name__)


def send_report(html_path: str, cfg: dict, date_str: str,
                items: list[NewsItem] | None = None,
                highlights: list[str] | None = None,
                intranet_guide: list[str] | None = None) -> None:
    m = cfg.get("mail", {})
    host, port = m.get("smtp_host", ""), m.get("smtp_port", 465)
    if not host:
        raise RuntimeError("config.yaml 中 mail.smtp_host 未配置")

    title = cfg.get("report", {}).get("title", "知识库前沿新闻推送")
    subject = f"{m.get('subject_prefix', '')} {date_str}"

    # 邮件正文: 有结构化数据时生成手机端友好版; 否则退化为内嵌报告文件
    if items:
        body_html = build_html(title, date_str, items, highlights or [], intranet_guide or [])
        body_text = build_text(title, date_str, items, highlights or [], intranet_guide or [])
        # 留存一份邮件正文副本, 便于版式调试
        preview = os.path.splitext(html_path)[0] + "_email.html"
        with open(preview, "w", encoding="utf-8") as f:
            f.write(body_html)
        log.info("邮件正文预览已保存: %s", preview)
    else:
        with open(html_path, "r", encoding="utf-8") as f:
            body_html = f.read()
        body_text = f"{title} {date_str} - 请查看附件中的完整报告。"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr(("KB-Ontology-News", m.get("from_addr", "")))
    msg["To"] = ", ".join(m.get("to_addrs", []))

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_text, "plain", "utf-8"))
    alt.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(alt)

    with open(html_path, "rb") as f:
        att = MIMEApplication(f.read())
        att.add_header("Content-Disposition", "attachment",
                       filename=os.path.basename(html_path))
        msg.attach(att)

    username = m.get("username") or ""
    # 优先读明文 password 字段; 为空则读环境变量(更安全的方式)
    password = m.get("password") or ""
    if not password and m.get("password_env"):
        password = os.environ.get(m["password_env"], "")

    cls = smtplib.SMTP_SSL if m.get("use_ssl", True) else smtplib.SMTP
    with cls(host, port, timeout=30) as smtp:
        if not m.get("use_ssl", True):
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.sendmail(m.get("from_addr"), m.get("to_addrs", []), msg.as_string())
    log.info("邮件已发送至 %s", m.get("to_addrs"))
