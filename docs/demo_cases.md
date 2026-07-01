# Demo 研究案例

## Demo 1: 动力电池行业竞争格局分析

**输入**:
```
分析中国动力电池行业竞争格局
研究类型：行业分析
```

**执行流程**:
1. ChiefArchitect → 分类为"行业分析"，生成11章节大纲
2. DeepScout → 检索到25+条结果，提取18条关键事实
3. DataAnalyst → 查询5家公司财务数据，计算CAGR和排名
4. CodeWizard → 生成市场份额饼图 + 营收对比柱状图
5. LeadWriter → 生成4500字中文Markdown报告
6. CriticMaster → 综合评分87分 → Complete

**报告内容**:
- 行业规模：2025年18500亿元
- 市场份额：宁德时代45%，比亚迪29%
- CR3达78%
- 磷酸铁锂占比67%
- 5家核心企业财务对比表
- 政策梳理 + 风险分析

---

## Demo 2: 宁德时代 vs 比亚迪财务对比

**输入**:
```
对比宁德时代和比亚迪的财务表现与行业竞争力
研究类型：竞品分析
```

**执行流程**:
1. ChiefArchitect → 分类为"竞品分析"
2. DeepScout → 检索公司公告、券商研报
3. DataAnalyst → 查询两家公司2022-2025财务数据
4. CodeWizard → 雷达图 + 横向对比柱状图
5. LeadWriter → 生成竞品对比报告
6. CriticMaster → 综合评分84分 → Revise（补充可读性）
7. LeadWriter → 优化报告结构
8. CriticMaster → 综合评分87分 → Complete

**报告内容**:
- 营收对比：宁德2024年5230亿 vs 比亚迪7800亿
- 利润对比：宁德净利率11.7% vs 比亚迪5.4%
- 雷达图多维对比（营收/利润/毛利率/ROE/份额）
- SWOT分析
- 投资建议

---

## Demo 3: 低空经济综合研究

**输入**:
```
分析低空经济行业政策、市场规模、核心公司与风险因素
研究类型：综合研究
```

**执行流程**:
1. ChiefArchitect → 分类为"综合研究"
2. DeepScout → 检索政策文件、行业报告、公司信息
3. DataAnalyst → 查询低空经济行业数据
4. CodeWizard → 市场规模趋势折线图
5. LeadWriter → 生成综合研究报告
6. CriticMaster → 综合评分85分 → Complete

**报告内容**:
- 市场规模：2025年1.2万亿元，预计2030年突破5万亿
- 政策梳理：28个省份出台相关政策
- eVTOL适航认证突破
- 核心企业分析
- 风险因素识别

---

## 运行 Demo

```bash
# 1. 启动后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. 运行 Demo（通过 API）
curl -X POST http://localhost:8000/api/research/create \
  -H "Content-Type: application/json" \
  -d '{"query": "分析中国动力电池行业竞争格局", "research_type": "行业分析", "use_mock": true}'

# 3. 启动研究（使用返回的 task_id）
curl -X POST http://localhost:8000/api/research/run/{task_id}

# 4. 查看状态
curl http://localhost:8000/api/research/status/{task_id}

# 5. 获取结果
curl http://localhost:8000/api/research/result/{task_id}
```
