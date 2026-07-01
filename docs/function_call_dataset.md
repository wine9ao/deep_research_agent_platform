# FunctionCall 数据构建 Pipeline

## 概述

从 Agent 执行日志中自动构建 FunctionCall 训练数据集，用于训练智能体工具选择和参数推理能力。

## Pipeline 流程

```
execution_logs
    │
    ▼
extract_logs.py       → 从日志提取结构化样本
    │
    ▼
build_seed_dataset.py → 生成 3,030 条种子样本
    │
    ▼
augment_dataset.py    → 模板改写 + 上下文拼接 → 7,612 条
    │
    ▼
balance_dataset.py    → 按标签/Agent/工具平衡分布
    │
    ▼
export_train_jsonl.py → train.jsonl / valid.jsonl / test.jsonl
                      → dataset_report.md
```

## 数据格式

```json
{
  "id": "seed_000001",
  "task": "分析动力电池行业竞争格局",
  "context": "用户需要行业分析报告，需要检索政策、市场份额和公司信息",
  "agent": "DeepScout",
  "available_tools": ["WebSearchTool", "LocalKnowledgeBaseTool", "FinancialDataAPITool"],
  "expected_tool": "WebSearchTool",
  "arguments": {
    "query": "动力电池 行业规模 市场份额 2025",
    "top_k": 5
  },
  "label": "success",
  "route_type": "行业分析",
  "reason": "该任务需要优先检索行业公开信息"
}
```

## 失败类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `misroute` | 误路由 | 应使用 WebSearch 但调用了 FinancialAPI |
| `wrong_tool` | 误选工具 | 应使用 DataAnalysis 但调用了 ChartGeneration |
| `missing_params` | 参数缺失 | 缺少必需的 query 参数 |
| `chain_break` | 链式断裂 | 上一步输出格式不符合下一步输入 |
| `unsafe_sql` | SQL 不安全 | 生成的 SQL 包含 DELETE 语句 |
| `low_relevance` | 检索低相关 | 检索结果与问题相关性低 |

## 使用方式

```bash
cd data_pipeline

# 完整 pipeline
python export_train_jsonl.py --full-pipeline

# 分步执行
python build_seed_dataset.py
python augment_dataset.py
python balance_dataset.py
python export_train_jsonl.py

# 输出文件
# data/exports/train.jsonl     (~6000 条)
# data/exports/valid.jsonl     (~800 条)  
# data/exports/test.jsonl      (~800 条)
# data/exports/dataset_report.md
```

## 数据统计

- 覆盖 6 个 Agent 类型
- 覆盖 9 个工具
- 覆盖 6 种研究类型
- 失败样本占比 ~20%
- 中文任务为主
