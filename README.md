# 每日 AI 情报飞书机器人

面向开源模型产品经理与战略经理的轻量日报。每天汇总中国与海外科技新闻、模型官方资讯、论文、播客及会议动态，按主题筛选并附原文链接。日报中的“信号”是入选文章的关键词统计；“产品关注”和“战略关注”指向相关原文，不代替对原文的核查。

## 运行

需要 Python 3.12；项目仅使用标准库，无需安装依赖。

```bash
cd /workspace/aipm
python3 -m ai_digest                 # 抓取并在终端预览，不发送
FEISHU_WEBHOOK_TOKEN=... python3 -m ai_digest --send
python3 -m unittest discover -s tests -v
```

在飞书群添加**自定义机器人**，从 Webhook URL `https://open.feishu.cn/open-apis/bot/v2/hook/<token>` 中取出 `<token>`，以 `FEISHU_WEBHOOK_TOKEN` 注入。不要把完整 Webhook 或 token 提交到仓库。机器人若启用签名校验，此版本尚不支持；可使用仅绑定群且妥善保管的 Webhook token，并按飞书管理要求配置安全策略。

`.github/workflows/daily-digest.yml` 在每天北京时间 11:00 触发，也支持在 GitHub Actions 页面手动运行并立即推送。要启用定时发送，先把代码推到仓库默认分支 `main`，再在 GitHub 仓库的 Actions secrets 中配置 `FEISHU_WEBHOOK_TOKEN`。GitHub 定时任务可能延迟启动。云环境中的变量与 GitHub Actions secrets 分别配置。飞书自定义群机器人只能接收 Webhook 推送，不能响应群内 `@机器人` 命令；若需要群内命令，需要另建飞书应用机器人和公开可达的事件接收服务。

## 数据源与筛选

[`sources.json`](sources.json) 配置了量子位、TechCrunch AI、MIT Technology Review、Hugging Face、Latent Space、arXiv、NeurIPS 官方博客。每个来源要提供带发布日期的 RSS 或 Atom 条目。项目只抓取标题、摘要和原文链接，不抓取或转载全文。来源若无新条目则不会出现在当日报告中。采集失败会在报告末尾标出；全部失败则不会发送。

默认窗口为最近 48 小时，最多 10 条，每个来源最多 2 条，并优先给中国新闻、海外新闻、官方消息、论文、播客、会议各留一个位置。没有符合条件的新条目时发送空日报；全部来源失败时不发送。`--hours`、`--limit` 可以调整。分类和排序是规则筛选，尚未做模型生成的深度分析或事实核查。

新增来源时在 `sources.json` 加一项，类别用 `news`、`official`、`paper`、`podcast` 或 `conference`，地区用 `CN` 或 `GLOBAL`。优先使用机构自身公开的 RSS/Atom，避免不稳定的第三方转发。上线前应逐一验证来源的可用性和授权条款。

## 云环境验证

```bash
cd /workspace/aipm
python3 -m unittest discover -s tests -v
python3 -m ai_digest --fixture-dir tests/fixtures --config tests/fixtures/sources.json --now 2026-10-08T02:00:00+00:00
python3 -m ai_digest
```

第三条命令访问真实来源。云环境需允许访问 `www.qbitai.com`、`techcrunch.com`、`www.technologyreview.com`、`huggingface.co`、`www.latent.space`、`export.arxiv.org` 和 `blog.neurips.cc`；发送还需 `open.feishu.cn`。Webhook token 缺失时仍可预览日报。
