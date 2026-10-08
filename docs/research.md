# 开源项目调研：AI 产品与战略情报日报

2026-10-08 在各项目的 GitHub 页面核对了 Star / Fork 数量，并阅读项目 README。数量是当日快照，会继续变化；Star 和 Fork 是社区采用信号，不直接代表资讯准确性。只借鉴产品方法，未复制项目代码。

| 项目 | Star / Fork | Fork / Star | 值得借鉴的做法 |
| --- | ---: | ---: | --- |
| [TrendRadar](https://github.com/sansan0/TrendRadar) | 62,724 / 24,882 | 39.7% | RSS 与多平台来源、GUID 优先去重、每组数量限制、飞书推送和增量模式。 |
| [Horizon](https://github.com/Thysrael/Horizon) | 9,564 / 1,481 | 15.5% | 按内容类型配置筛选标准，控制类别占比，给不同读者提供不同的解释角度。 |
| [ai-daily-digest](https://github.com/vigorX777/ai-daily-digest) | 1,647 / 179 | 10.9% | 时间过滤、并发采集、多维排序及结构化日报。其 AI 摘要需要额外模型凭据。 |
| [agents-radar](https://github.com/duanyytop/agents-radar) | 1,119 / 217 | 19.4% | 直接跟踪开源项目活动，在日报中提炼开源生态与战略信号。 |
| [Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) | 7,193 / 852 | 11.8% | 将市场情报转成产品定位、竞争比较和待验证的决策问题。它本身不是新闻采集器。 |

## 本项目采用的改进

1. 添加 vLLM、SGLang、Transformers、Ollama 的官方 GitHub Releases Atom 源，补足开源生态的直接发布信号。这些订阅地址已实际返回 Atom 内容。
2. 对 RSS GUID / Atom ID、标准化 URL 和标题去重；每个来源及内容类别均限量，减少重复与单一话题占版。
3. 最多并发抓取 4 个来源，保留单源失败诊断；日报的信号计数附代表性原文链接。
4. 产品与战略关注均写成需核查的问题，避免从标题和短摘要推断未经证实的结论。

未引入上述项目的模型摘要、跨站全文抓取或社区评论。当前没有可用的模型密钥，来源内容也未做全文事实核查；日报继续明确标注证据与来源失败。
