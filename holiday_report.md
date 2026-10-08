**国庆假期 AI 情报补刊｜10 月 1—7 日（北京时间）**
面向开源模型产品经理与战略经理。按来源可靠性、产品/生态影响和时间筛选，去重后保留 15 条；以下均附原文，厂商性能主张需独立验证。

**假期主线**
• **模型竞争：**Google、Mistral、Reflection 公布新模型；其中 Mistral ML4 和 Beam 的权重截至 10 月 7 日尚未开放，评估时要区分发布消息与可部署版本。
• **推理成本：**模型路由、服务框架和 KV 缓存压缩继续推进；成本收益应放到自身任务与硬件上复测。
• **智能体落地：**建站操作、网站访问与用户授权成为产品体验的关键环节。

**中国团队与市场**
• [openJiuwen X-Router 模型路由发布](https://www.qbitai.com/2026/10/500098.html) · 量子位/项目代码 · 10-02
  摘要：X-Router 按任务复杂度在本地与云端模型间路由；[代码与用法](https://github.com/openJiuwen-ai/model-router/blob/main/python/openjiuwen/x_router/README.md)已公开，节省 Token 的报道数据仍需复测。
• [Meshy 入选 a16z 消费级 AI 月收入榜](https://www.qbitai.com/2026/10/501791.html) · 量子位转载 Meshy 稿件 · 10-07
  摘要：Meshy 称其在 a16z 美国消费者月收入榜列第 31；这是公司提供的报道，排名及市场外推应核对原榜单。

**海外模型、产品与治理**
• [Google 发布 Gemini 4 Argon](https://techcrunch.com/2026/09/30/google-releases-gemini-4-argon-called-its-most-powerful-model-yet/) · TechCrunch · 北京时间 10-01
  摘要：Google 强调新模型的编码与防御性网络安全能力，首批仅向经筛选的安全合作伙伴开放。
• [Shopify 推出对话式建站 Canvas](https://techcrunch.com/2026/10/01/shopify-debuts-canvas-a-way-to-build-online-stores-by-chatting-with-ai/) · TechCrunch · 10-02
  摘要：商家可与 Sidekick 对话搭建店铺，Canvas 实时呈现可交互的实际页面，减少手动改主题与代码。
• [Reflection 公布 Beam 模型](https://techcrunch.com/2026/10/05/reflection-debuts-beam-a-open-weight-ai-model-to-rival-chinese-models-at-lower-compute-cost/) · TechCrunch · 10-06
  摘要：Beam 是 5010 亿总参数、230 亿激活参数的 MoE；公司称推理成本较低，但权重与完整技术细节计划稍后公开。
• [Mistral 发布 Mistral Large 4](https://techcrunch.com/2026/10/06/mistrals-new-1t-model-aims-to-leapfrog-closed-and-open-rivals/) · TechCrunch · 10-06
  摘要：这款约 1 万亿参数的多模态模型目前仅通过受限端点使用；Mistral 计划完成安全测试后再开放权重。
• [网站屏蔽成为消费级智能体障碍](https://techcrunch.com/2026/10/06/the-next-hurdle-for-ai-agents-getting-websites-to-let-them-in/) · TechCrunch · 10-07
  摘要：购物与预订智能体遭遇网站主动屏蔽或反爬措施，第三方站点接入正限制端到端任务完成。
• [Google 开放 SynthID 检测网站](https://techcrunch.com/2026/10/07/googles-new-synthid-website-can-identify-ai-generated-media/) · TechCrunch · 10-07
  摘要：公众可检查图片、视频和音频中的 SynthID 水印；未检出水印不能证明内容并非 AI 生成。

**开源工具与推理生态**
• [Ai2 开源 AstaBrief 8B](https://huggingface.co/blog/allenai/astabrief) · Hugging Face 官方博客 · 10-02
  摘要：模型根据研究问题与检索文献摘录生成带引文的报告，为可本地部署的研究助手提供组件。
• [SGLang v0.5.21](https://github.com/sgl-project/sglang/releases/tag/v0.5.21) · GitHub 发布 · 10-03
  摘要：版本新增 DeepSeek-V4.1 Flash 等模型支持，并汇入大量社区更新；实际性能与兼容性需测试。
• [vLLM v0.31.0](https://github.com/vllm-project/vllm/releases/tag/v0.31.0) · GitHub 发布 · 10-06
  摘要：版本加入 DeepSeek-V4.1 Flash 相关推理优化，涉及 FlashMLA 与 DeepGEMM，适合评估部署收益。
• [Ollama v0.40.0](https://github.com/ollama/ollama/releases/tag/v0.40.0) · GitHub 发布 · 10-07
  摘要：在 Apple Silicon 上，受支持的模型架构默认改用 MLX 运行，并扩展了嵌入模型支持。

**论文与播客**
• [TaSQ：1-bit KV 缓存压缩](https://arxiv.org/abs/2610.03027v1) · arXiv · 10-02
  摘要：作者提出 1-bit KV 缓存压缩，并在单卡 SGLang 实验中报告峰值吞吐较 BF16 基线提高 1.87 倍。
• [DelegationBench：智能体何时应先询问用户](https://arxiv.org/abs/2610.05532v1) · arXiv · 10-05
  摘要：156 个情境测试显示，模型真正调用工具时，比只判断拟议动作时更少向用户征询许可。
• [云原生智能体运行环境讨论](https://www.latent.space/p/stacklok) · Latent Space 播客 · 10-07
  摘要：访谈 Kubernetes 共同创建者 Craig McLuckie 和 Joe Beda，讨论将智能体运行环境从桌面迁向云端。

**开工后优先核查**
产品：测试智能体在第三方网站受阻时的降级流程，以及执行有后果操作前的授权边界。
战略：分别跟踪模型公告、权重可用性、许可证与独立基准；对路由和推理优化用自身负载复测成本。
