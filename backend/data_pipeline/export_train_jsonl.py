"""Export the balanced dataset as train/valid/test JSONL splits.

Outputs:
- train.jsonl (80% of data)
- valid.jsonl (10% of data)
- test.jsonl (10% of data)
- dataset_report.md (statistics report)
"""

from __future__ import annotations

import json
import os
import random
from collections import Counter
from datetime import datetime
from typing import Any


def export_splits(
    input_path: str = "balanced_dataset.json",
    output_dir: str = "data/exports",
    train_ratio: float = 0.8,
    valid_ratio: float = 0.1,
    seed: int = 42,
) -> dict[str, str]:
    """Export dataset to train/valid/test JSONL splits.

    Args:
        input_path: Path to balanced dataset JSON.
        output_dir: Directory for output files.
        train_ratio: Fraction for training set.
        valid_ratio: Fraction for validation set.
        seed: Random seed for reproducibility.

    Returns:
        dict mapping split names to file paths.
    """
    random.seed(seed)

    with open(input_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    print(f"Total samples: {len(samples)}")

    # Shuffle
    random.shuffle(samples)

    # Split
    n = len(samples)
    n_train = int(n * train_ratio)
    n_valid = int(n * valid_ratio)

    train = samples[:n_train]
    valid = samples[n_train:n_train + n_valid]
    test = samples[n_train + n_valid:]

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Save splits
    splits = {
        "train": os.path.join(output_dir, "train.jsonl"),
        "valid": os.path.join(output_dir, "valid.jsonl"),
        "test": os.path.join(output_dir, "test.jsonl"),
    }

    for split_name, split_data in [("train", train), ("valid", valid), ("test", test)]:
        filepath = splits[split_name]
        with open(filepath, "w", encoding="utf-8") as f:
            for sample in split_data:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        print(f"  {split_name}: {len(split_data)} samples → {filepath}")

    # Generate report
    report_path = os.path.join(output_dir, "dataset_report.md")
    _generate_report(train, valid, test, report_path)
    print(f"  Report → {report_path}")

    return splits


def _generate_report(
    train: list[dict], valid: list[dict], test: list[dict], report_path: str
) -> None:
    """Generate a dataset statistics report in Markdown."""
    all_data = train + valid + test

    lines = [
        "# FunctionCall 训练数据集统计报告\n",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "## 一、数据集概况\n",
        f"- 总样本数：**{len(all_data)}**",
        f"- 训练集：**{len(train)}**（{len(train)/max(len(all_data),1)*100:.1f}%）",
        f"- 验证集：**{len(valid)}**（{len(valid)/max(len(all_data),1)*100:.1f}%）",
        f"- 测试集：**{len(test)}**（{len(test)/max(len(all_data),1)*100:.1f}%）\n",
        "## 二、标签分布\n",
        "| 标签 | 训练集 | 验证集 | 测试集 | 总计 |",
        "|------|--------|--------|--------|------|",
    ]

    all_labels = set(s["label"] for s in all_data)
    for label in sorted(all_labels):
        t_c = sum(1 for s in train if s["label"] == label)
        v_c = sum(1 for s in valid if s["label"] == label)
        te_c = sum(1 for s in test if s["label"] == label)
        lines.append(f"| {label} | {t_c} | {v_c} | {te_c} | {t_c + v_c + te_c} |")

    lines.extend([
        "\n## 三、Agent 分布\n",
        "| Agent | 训练集 | 验证集 | 测试集 | 总计 |",
        "|-------|--------|--------|--------|------|",
    ])

    all_agents = set(s["agent"] for s in all_data)
    for agent in sorted(all_agents):
        t_c = sum(1 for s in train if s["agent"] == agent)
        v_c = sum(1 for s in valid if s["agent"] == agent)
        te_c = sum(1 for s in test if s["agent"] == agent)
        lines.append(f"| {agent} | {t_c} | {v_c} | {te_c} | {t_c + v_c + te_c} |")

    lines.extend([
        "\n## 四、工具分布\n",
        "| 工具 | 训练集 | 验证集 | 测试集 | 总计 |",
        "|------|--------|--------|--------|------|",
    ])

    all_tools = set(s["expected_tool"] for s in all_data)
    for tool in sorted(all_tools):
        t_c = sum(1 for s in train if s["expected_tool"] == tool)
        v_c = sum(1 for s in valid if s["expected_tool"] == tool)
        te_c = sum(1 for s in test if s["expected_tool"] == tool)
        lines.append(f"| {tool} | {t_c} | {v_c} | {te_c} | {t_c + v_c + te_c} |")

    lines.extend([
        "\n## 五、失败类型分布\n",
        "| 失败类型 | 数量 |",
        "|----------|------|",
    ])

    fail_counts = Counter(
        s["label"] for s in all_data if s["label"] != "success"
    )
    for ftype, count in fail_counts.most_common():
        lines.append(f"| {ftype} | {count} |")

    lines.extend([
        "\n## 六、研究类型分布\n",
        "| 研究类型 | 数量 |",
        "|----------|------|",
    ])

    type_counts = Counter(s.get("route_type", "") for s in all_data)
    for rtype, count in type_counts.most_common():
        lines.append(f"| {rtype} | {count} |")

    lines.extend([
        "\n## 七、数据质量说明\n",
        "- 所有样本均来自 agent execution logs 或经过模板增强",
        "- 失败类型样本约占 20%，模拟真实的错误场景",
        "- 数据集覆盖 6 个 Agent、9 个工具、6 种研究类型",
        "- 建议在模型微调时使用 weighted sampling 处理类别不平衡",
    ])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    """Run the export pipeline end-to-end."""
    import argparse

    parser = argparse.ArgumentParser(description="Export train/valid/test JSONL splits")
    parser.add_argument("--input", "-i", default="balanced_dataset.json")
    parser.add_argument("--output-dir", "-o", default="data/exports")
    parser.add_argument("--full-pipeline", action="store_true", help="Run full pipeline from seed")
    args = parser.parse_args()

    if args.full_pipeline:
        from build_seed_dataset import build_seed_dataset
        from augment_dataset import augment_dataset
        from balance_dataset import balance_dataset

        print("=" * 50)
        print("Running full data pipeline...")
        print("=" * 50)

        if not os.path.exists("seed_dataset.json"):
            build_seed_dataset()
        if not os.path.exists("augmented_dataset.json"):
            augment_dataset()
        if not os.path.exists("balanced_dataset.json"):
            balance_dataset()

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        print("Run with --full-pipeline to generate data from scratch")
        return

    export_splits(args.input, args.output_dir)
    print("\nDone!")


if __name__ == "__main__":
    main()
