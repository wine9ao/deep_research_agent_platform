# 面试问答准备

## 一、架构设计

### Q: 为什么用 6 个 Agent 而不是一个 Agent 搞定所有事？

单一 Agent 面对复杂研究任务时 context 太长、指令冲突、容易遗漏。6 Agent 拆分的核心逻辑是**把研究流程本身结构化**——规划、检索、分析、图表、撰写、评审天然就是六个独立环节，每个 Agent 只关注自己的输入输出，不互相干扰。类比软件开发里的微服务：一个超大单体不如拆成职责清晰的 6 个模块。

### Q: Agent 之间怎么通信？

通过全局 Pydantic `ResearchState`（30+ 字段），不是发消息，而是**共享状态**。每个 Agent 读取前序 Agent 的输出字段，执行自己的逻辑，然后写入新字段。比如 DeepScout 写完 `facts` 和 `evidence_list`，LeadWriter 读取这些字段来写报告。状态变更通过 `execution_logs` 完整记录，`checkpoint` 支持断点恢复。

### Q: 为什么用 LangGraph 而不是自己写编排？

LangGraph 提供了状态图原语（node、edge、conditional edge），天然适合有分支和循环的工作流。项目里的 Review Loop 就是一个 conditional edge：CriticMaster 输出 `complete/re_research/revise`，Router 根据分数决定下一步走向哪，形成闭环。自己写也能做，但 LangGraph 的表达更清晰，面试官一看就懂流程。

---

## 二、LLM 相关

### Q: 怎么适配多个 LLM 提供商？

OpenAI-compatible API 已经是事实标准——DeepSeek、通义千问、Kimi、GLM、Ollama 全都兼容 `POST /v1/chat/completions`。项目里 `LLMClient` 封装了一个 `AsyncOpenAI` 客户端，`.env` 里改 `OPENAI_BASE_URL` + `LLM_MODEL` + `OPENAI_API_KEY` 就可以切模型，不改一行代码。

### Q: Agent 调用 LLM 的具体方式是什么？

两种调用模式：`chat()` 返回自由文本（LeadWriter 写报告用），`chat_json()` 返回结构化 JSON（ChiefArchitect 出大纲、CriticMaster 出评分用）。System prompt 定义角色和输出格式，User message 塞入当前上下文（facts、evidence、outline 等）。比如 LeadWriter 一次调用会带上 8000 字的研究数据作为上下文，让 LLM 基于这些数据写报告而不是凭空编造。

### Q: LLM 挂了怎么办？

每个 Agent 的 `execute()` 里都有 try/except，LLM 调用失败自动走 fallback。比如 ChiefArchitect fallback 是关键词匹配分类 + 固定模板大纲，CriticMaster fallback 是规则打分（数字数量、章节覆盖度等）。无 API Key 也能跑通完整流程。

---

## 三、检索与工具

### Q: 混合检索是怎么做的？

两条检索管线并行，结果加权合并：
- **向量检索**（语义匹配）：文本 → embedding → FAISS/Milvus 余弦相似度，搜"动力电池"能找到"锂电池""车用储能"
- **关键词检索**（精确匹配）：BM25 或 Elasticsearch match query，搜"宁德时代营收"精确命中包含这些词的文档

两条管线各返回 top_k × 2 个结果，score 加权 0.5 + 0.5 合并，取 top_k 返回。语义覆盖广度 + 关键词保证精度。

### Q: Text2SQL 怎么保证安全？

两道防线：sqlglot 做语法级解析，识别 SELECT/DELETE/DROP 等语句类型，只要不是 SELECT/WITH 就拦截；regex 做关键词兜底，扫描 DELETE、INSERT、UPDATE 等关键字。双重校验过了才在 SQLite 上执行。不会出现"LLM 生成的 DROP TABLE"被执行的情况。

### Q: 为什么设计多后端适配器？

项目定位是可演示的 MVP，同时要体现工程化能力。Mock 后端保证零配置就能跑，Tavily/Zilliz Cloud/AKShare 等真实后端体现生产可用性。适配器模式的好处是新增加一个后端不需要改动任何 Agent 代码——比如后续想换成 Google Search，只需新写一个 50 行的 backend 类，`.env` 里改一行配置即可。

---

## 四、评审与路由

### Q: CriticMaster 怎么评分？路由逻辑是什么？

7 个维度：完整性、事实准确性、逻辑性、引用质量、数据充分性、可读性，权重加权得出 final_score。路由规则：≥85 分 Complete；事实或数据 <75 分 Re-Research（回到检索）；可读性或逻辑 <75 分 Revise（回到撰写）。最多循环 3 轮，分数连续下降会提前止损（防止越改越差）。

### Q: 怎么防止幻觉？

三处防幻觉设计：一是 LeadWriter 的 prompt 明确要求"基于以下研究数据撰写，信息不足处标注'尚待补充'，不要编造"；二是 CriticMaster 专门检测幻觉风险（用 LLM 检查报告里的数据能否在检索结果中找到对应来源）；三是所有事实必须标注来源（`cited_sources`）。

---

## 五、工程细节

### Q: ResearchState 字段这么多，怎么保证一致性？

Pydantic v2 的类型系统。每个字段都有默认值，Agent 不会因为读不到字段而崩溃。`add_log()`、`add_error()`、`update_timestamp()` 等方法封装了常用操作。全局只有一个 State 实例在 Graph 里流转，不存在多副本不一致的问题。

### Q: 前端轮询为什么要 2 秒？

后端任务执行是异步的（`asyncio.create_task`），前端通过轮询 `/api/research/status/{task_id}` 获取进度。一次完整研究约 60-90 秒，2 秒轮一次够及时，也不会给后端造成压力。状态变 completed 后延迟 3 秒再跳转结果页，给数据库落盘留时间。

### Q: FunctionCall 数据 Pipeline 的价值是什么？

这个 Pipeline 展示了"从系统日志到训练数据"的完整链路。如果未来要微调一个专门做研究任务的模型，这些数据可以直接用。6 种失败类型（误路由、误选工具等）的标注帮助模型学习"什么情况下该用什么工具"。面试时强调"数据飞轮"的概念——系统运行 → 产生日志 → 提取训练数据 → 优化模型 → 系统更好用。

---

## 六、可能追问

### Q: 为什么不用 LangChain 的 Agent 框架？

LangChain 的 AgentExecutor 是通用框架，对研究场景的定制性不够。LangGraph 给了更底层的图编排能力，可以精确控制每个节点的输入输出和路由条件。项目里只需要 `StateGraph` + `add_node` + `add_conditional_edges` 就完成了，比 LangChain 更轻量。

### Q: 6 个 Agent 是串行还是并行？

串行。研究场景天然有依赖关系——没规划好就没法检索，没检索到就没法分析，分析完了才能写报告。不过 DeepScout 内部的 6 条搜索是并发的（多个 query 同时发请求）。

### Q: 图表怎么生成的？为什么用 ECharts 不用 Matplotlib？

图表不走 Python 渲染，而是生成 ECharts JSON spec，直接交给前端 `echarts-for-react` 渲染。好处是不依赖服务端图形库、响应式自适应、交互支持（悬停、缩放）。LLM 负责把分析数据映射成 `{labels: [...], series_data: [...]}` 格式，`ChartGenerationTool` 补全完整的 ECharts option。

### Q: 如果让你重做这个项目，会改什么？

三点：一是用真正的 embedding 模型（如 BGE-M3）替代 hash embedding，语义检索质量会大幅提升；二是把 Agent 改为异步并行——当前串行链路里 DeepScout 和 DataAnalyst 其实可以并行（检索和分析数据用的是不同数据源）；三是加一个最终报告缓存，相同 query 短时间内复用结果，减少 LLM 调用成本。
