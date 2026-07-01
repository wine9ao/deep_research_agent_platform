# 多 Agent 工作流说明

## 工作流概览

```
START
  │
  ▼
ChiefArchitect (规划)
  │
  ▼
DeepScout (检索)
  │
  ▼
DataAnalyst (分析)
  │
  ▼
CodeWizard (图表)
  │
  ▼
LeadWriter (撰写)
  │
  ▼
CriticMaster (评审)
  │
  ├── Complete → END
  ├── Re-Research → DeepScout
  └── Revise → LeadWriter
```

## Agent 详细说明

### 1. ChiefArchitect — 规划 Agent

**职责**: 理解研究任务，制定研究策略

**输入**: `user_query`

**处理流程**:
1. 分类研究类型（行业分析/公司分析/财务分析/竞品分析/政策分析/综合研究）
2. 拆解研究问题
3. 生成研究大纲（11 章节标准结构）
4. 制定检索计划（Query Expansion → 6+ 条搜索计划）
5. 确定数据需求和预期图表

### 2. DeepScout — 检索 Agent

**职责**: 执行多源信息检索

**ReAct 循环**:
- **Thought**: 分析搜索计划，确定检索策略
- **Action**: 并行调用 WebSearch + KnowledgeBase
- **Observation**: 收集并评分检索结果
- **Reflection**: 检查信息缺口

**输出**: 原始结果 → 去重排序 → 证据提取 → 缺口识别

### 3. DataAnalyst — 数据分析 Agent

**职责**: 查询和分析结构化数据

**处理流程**:
1. 从 query + facts 中识别公司名和行业名
2. 调用 FinancialDataAPI 获取财务数据
3. 执行多维分析：YoY、CAGR、排名、占比
4. 生成分析洞察和图表需求

### 4. CodeWizard — 可视化 Agent

**职责**: 生成图表 ECharts spec

**安全机制**: AST 检查 → 禁止 import os/subprocess/sys → 仅允许白名单模块

**图表类型**: line, bar, pie, radar, horizontal_bar, financial_trend

### 5. LeadWriter — 报告撰写 Agent

**职责**: 生成结构化中文 Markdown 报告

**报告结构**: 摘要 → 背景 → 市场 → 政策 → 产业链 → 竞争 → 财务 → 风险 → 展望 → 结论 → 附录

### 6. CriticMaster — 评审 Agent

**职责**: 7 维度质量评分 + 智能路由

**评分维度**: 完整性(25%) + 事实准确性(25%) + 逻辑性(15%) + 引用(10%) + 数据(15%) + 可读性(10%)

**路由规则**:
- final_score ≥ 85 → Complete
- factuality < 75 或 data < 75 → Re-Research
- readability < 75 或 logic < 75 → Revise
- iteration ≥ max → 强制 Complete
