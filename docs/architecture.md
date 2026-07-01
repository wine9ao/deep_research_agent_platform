# 系统架构文档

## 整体架构

Deep Research Agent Platform 采用前后端分离的微服务架构：

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│         React + Vite + TypeScript + Ant Design   │
│   ┌─────────┐ ┌──────────┐ ┌────────────────┐  │
│   │  Home   │ │ Progress │ │  ReportResult  │  │
│   └─────────┘ └──────────┘ └────────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ HTTP/REST
┌──────────────────────┴──────────────────────────┐
│                   Backend                        │
│                FastAPI + LangGraph               │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         Research Graph Engine             │   │
│  │  CA → DS → DA → CW → LW → CM → Router   │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌───────────────┐   │
│  │  Tools   │ │  Memory  │ │  Checkpoint   │   │
│  │  (9)     │ │  System  │ │  Manager      │   │
│  └──────────┘ └──────────┘ └───────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         Data Layer                        │   │
│  │  SQLite (SQLAlchemy) + Vector Store      │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

## 核心模块

### 1. Agent 模块 (`app/agents/`)

6 个专业 Agent，每个 Agent 负责研究流程的一个阶段：

- **ChiefArchitect**: 任务理解和研究规划
- **DeepScout**: 多源信息检索和证据收集
- **DataAnalyst**: 数据查询和分析
- **CodeWizard**: 图表生成和代码执行
- **LeadWriter**: 报告撰写
- **CriticMaster**: 质量评审和路由决策

### 2. Tools 模块 (`app/tools/`)

9 个工具，所有工具继承自 `BaseTool`，提供统一接口：

```python
class BaseTool:
    name: str
    description: str
    async def run(self, input: dict) -> dict
```

### 3. Graph 模块 (`app/graph/`)

基于 LangGraph 范式的状态图引擎：

- `ResearchGraph`: 执行完整的 6 Agent 流水线，包含 review loop
- `ResearchRouter`: 根据 CriticMaster 的评分决定下一步路由

### 4. State 模块 (`app/state/`)

- `ResearchState`: 全局 Pydantic 状态模型（34+ 字段）
- `CheckpointManager`: 异步状态持久化（SQLite）

### 5. Memory 模块 (`app/memory/`)

- `SessionMemory`: 当前任务上下文记忆
- `UserMemoryManager`: 用户偏好和历史记忆

## 数据流

```
User Query
    │
    ▼
ChiefArchitect ──→ research_type, outline, search_plan
    │
    ▼
DeepScout ──→ raw_search_results, facts, evidence_list
    │
    ▼
DataAnalyst ──→ structured_data, financial_metrics, analysis_insights
    │
    ▼
CodeWizard ──→ chart_specs, visualization_summary
    │
    ▼
LeadWriter ──→ draft_report, cited_sources
    │
    ▼
CriticMaster ──→ quality_scores, review_feedback
    │
    ▼
Router ──→ Complete / Re-Research / Revise
    │
    ▼
Final Report
```
