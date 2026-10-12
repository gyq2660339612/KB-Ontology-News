# KB-Ontology-News

知识库 / 知识图谱 / 本体论 **× AI Agent 最新进展**的每日新闻推送系统(《知识库前沿新闻推送》):
每天自动检索 GitHub 增速榜与国内外高质量技术社区,重点收录**知识库与 Agent 最新进展相结合**的项目与文章
(Agent 记忆、上下文工程、Agentic RAG、本体驱动的 Agent 等),生成图文并茂的 HTML 报告并通过邮件发送。

> 当前版本:v0.1 初版 —— 聚焦**信息检索 + 报告生成**;邮件发送已实现,配置后即可用。

## 功能与信息源

| 分类 | 来源 | 采集方式 |
|------|------|----------|
| GitHub 增速榜 | **GitHub Trending 日榜/周榜**(官方"涨星最快"榜,按主题关键词过滤)+ **新锐项目**(最近 120 天创建且 star 达标) | Trending 页面解析 + GitHub Search API(`GITHUB_TOKEN` 可选) |
| 国际论坛 | Hacker News(Algolia API,仅匹配标题)、arXiv(官方 Atom API)、Lobsters / HN Best(RSS) | HTTP API / RSS |
| 国内论坛 | 开源中国等 RSS 源(掘金/知乎/机器之心无公开 RSS,需自建 RSSHub 后接入) | RSS/Atom(失效源自动跳过,可在 `config.yaml` 增删) |

GitHub 版块聚焦**增速**而非成熟项目。增速榜单调研结论:
- **GitHub Trending**(日/周/月,含 "stars today/this week")—— 最权威,本系统采用;
- OSS Insight(PingCAP,按事件流增速)—— 2026-10 实测 API 数据不可用,未采用;
- Star History / GitStar Ranking —— 分别是增长曲线工具与总 star 榜,非增速榜;
- 本系统每日保存 `data/raw_YYYYMMDD.json` 快照,积累后可自行计算"日增/周增 star"做领域增速榜。

每条收录内容包含:**摘要、内容要点、实现了什么效果、内网可复现性评级(高/中/低 + 说明)**。

## 快速开始

```bash
pip install -r requirements.txt

# 在线采集并生成今日报告(输出到 output/)
python run_daily.py

# 用已有数据离线生成报告(演示/内网调试)
python run_daily.py --from-data data/sample_20261012.json

# 采集 + 生成 + 发邮件
python run_daily.py --send-email
```

邮件配置在 `config.yaml` 的 `mail` 段。当前已配置为**网易 163 邮箱**(smtp.163.com:465,SSL)
发送到公司邮箱。注意:163 邮箱 SMTP 需要的是「授权码」而非登录密码
(在 163 邮箱 设置 → POP3/SMTP/IMAP 中开启并获取);密码建议改从环境变量
`KB_NEWS_SMTP_PASSWORD` 读取,避免明文留在配置文件里。

## 每日自动运行

- **Windows 任务计划程序**:新建任务 → 触发器"每天 08:30" → 操作
  `D:\Yiqi\code\KB-Ontology-News\py312\python.exe run_daily.py --send-email`,起始位置填项目目录。
- **Linux cron**:`30 8 * * * cd /path/KB-Ontology-News && python run_daily.py --send-email >> logs/cron.log 2>&1`

## 邮件版式(内网手机端适配)

参考 [ai-news-daily](https://fangransto.github.io/ai-news-daily) 的"内容自足"思路,邮件正文为**手机端友好版**:

- 全部样式内联,零外部图片/资源——邮件客户端剥离 `<style>` 或禁用图片也能完整阅读;
- 标题/摘要/要点/效果/内网复现性全部写在正文里,**不点链接也能读完**;
- URL 以纯文本完整展示,客户端禁用超链接时可长按复制;
- 同时附 `text/plain` 纯文本兜底(multipart/alternative),附件为完整图文版 HTML(电脑端打开)。

每次发送会在 `output/` 留存一份 `*_email.html` 邮件正文预览,便于版式调试。
(若要网页存档版,建议部署到**内网** Web 服务器;GitHub Pages 从内网不可达,不解决手机端问题。)

## 发布到 GitHub Pages(可选)

报告是自包含 HTML(图片已本地化),天然适合静态托管。`--pages` 会把报告同步到
`docs/` 目录(`index.html` 为最新一期 + 每日存档 + `archive.html` 索引):

```bash
python run_daily.py --pages        # 生成 + 同步 docs/
git add docs && git commit -m "daily" && git push   # 推送后 Pages 自动更新
```

在仓库 Settings → Pages 选择 `main` 分支 `/docs` 目录即可,访问地址为
`https://<用户名>.github.io/KB-Ontology-News/`。
注意:**`config.yaml` 含邮箱授权码,已被 `.gitignore` 排除,切勿提交**;
仓库中只保留脱敏模板 `config.example.yaml`。

## 内网部署(可复现性)

系统本身只依赖 3 个纯 Python 包(requests / PyYAML / Jinja2),极易搬进内网:

1. **依赖离线安装**:外网机器执行
   `pip download -r requirements.txt -d packages/`,
   把整个目录(含 `packages/`)拷入内网后
   `pip install --no-index --find-links=packages/ -r requirements.txt`。
2. **网络出口**:采集需要访问 GitHub/arXiv/HN。若内网有 HTTP 代理,在
   `config.yaml` 的 `network.proxies` 配置即可;完全无外网时,可由外网机器定时运行
   `run_daily.py`,把生成的 `output/` 目录(HTML + 本地图片)同步进内网。
3. **图片本地化**:`report.localize_images: true`(默认)会把所有远程图片下载到
   `output/assets/` 并改写为相对路径——报告拷到内网打开依然图文并茂。
4. **邮件**:当前配置为网易 163 邮箱外发至公司邮箱,要求运行环境能访问
   `smtp.163.com:465`;若改为内网 SMTP 中继,通常无需认证,`mail.username` 留空即可。

## 目录结构

```
KB-Ontology-News/
├── config.yaml            # 信息源 / 关键词 / 邮件 / 网络配置
├── requirements.txt
├── run_daily.py           # 入口: 采集 -> 生成 -> (可选)邮件
├── src/
│   ├── models.py          # NewsItem 数据模型(摘要/要点/效果/内网复现)
│   ├── collectors/        # github / hackernews / arxiv / rss_feeds 采集器
│   ├── report/            # Jinja2 模板 + 生成器(图片本地化)
│   └── mailer.py          # SMTP HTML 邮件
├── data/                  # 采集原始数据 + 人工精选样例(sample_20261012.json)
└── output/                # 生成的日报 HTML + assets/(本地化图片)
```

## 已知边界与后续计划

- 国内站点(掘金/知乎/机器之心部分页面)RSS 覆盖率低,当前按 RSS 可达性收录;
  后续可在内网自建 RSSHub 并直接把其路由配进 `config.yaml`。
- 自动模式下「今日摘要」为规则兜底(取各条首句);预留了接入内网 LLM 端点
  生成编辑级摘要的位置,见 `src/report/generator.py: auto_highlights()`。
- arXiv/HN 自动条目的摘要目前取自原文前 280 字符,未做翻译;接入内网 LLM 后可
  自动翻译 + 凝练。
- 条目的「内网可复现性」评级在自动模式下留空,由人工或 LLM 补全;
  初版样例报告(`data/sample_20261012.json`)中的评级为人工编辑。
