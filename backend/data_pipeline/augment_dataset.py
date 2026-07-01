"""Augment the seed dataset through template rewriting and semantic variation.

Techniques:
1. Template rewriting — vary query phrasing while keeping intent
2. Multi-turn context splicing — build longer context chains
3. Semantic rewriting — replace keywords with synonyms
"""

from __future__ import annotations

import json
import os
import random
from copy import deepcopy
from typing import Any

# ── Augmentation transforms ───────────────────────────────────────────────

_QUERY_REWRITES = {
    "分析": ["研究", "深入分析", "探讨", "评估", "剖析", "洞察"],
    "竞争格局": ["竞争态势", "竞争环境", "市场格局", "行业格局", "竞争结构"],
    "行业": ["产业", "领域", "赛道", "市场"],
    "投资机会": ["投资价值", "投资前景", "投资潜力", "增长机会"],
    "对比": ["比较", "横向对比", "对比分析", "对标"],
}

_COMPANY_ALIASES = {
    "宁德时代": ["CATL", "宁德时代新能源", "宁德"],
    "比亚迪": ["BYD", "比亚迪股份"],
    "动力电池": ["锂电池", "动力蓄电池", "车用电池"],
    "AI算力": ["人工智能算力", "智能算力", "AI计算"],
    "低空经济": ["低空空域经济", "城市空中交通", "UAM产业"],
}


def augment_dataset(
    input_path: str = "seed_dataset.json",
    output_path: str = "augmented_dataset.json",
    target_count: int = 7612,
) -> list[dict]:
    """Augment the seed dataset to reach the target count.

    Args:
        input_path: Path to the seed dataset.
        output_path: Path to save augmented dataset.
        target_count: Target number of samples (default 7612).

    Returns:
        Augmented list of samples.
    """
    random.seed(42)

    with open(input_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    print(f"Loaded {len(samples)} seed samples. Augmenting to {target_count}...")

    augmented = list(samples)  # Start with originals

    while len(augmented) < target_count:
        source = random.choice(samples)

        # Choose augmentation strategy
        strategy = random.choice(["rewrite", "context_extend", "semantic_swap"])

        new_sample = deepcopy(source)

        if strategy == "rewrite":
            new_sample = _template_rewrite(new_sample)
        elif strategy == "context_extend":
            new_sample = _context_extend(new_sample, augmented)
        elif strategy == "semantic_swap":
            new_sample = _semantic_swap(new_sample)

        new_sample["id"] = f"aug_{len(augmented):06d}"
        augmented.append(new_sample)

    # Save
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(augmented, f, ensure_ascii=False, indent=2)

    print(f"Augmented dataset: {len(augmented)} samples → {output_path}")
    return augmented


def _template_rewrite(sample: dict) -> dict:
    """Rewrite the task query using template variations."""
    task = sample["task"]
    for original, variations in _QUERY_REWRITES.items():
        if original in task:
            replacement = random.choice(variations)
            task = task.replace(original, replacement, 1)
            sample["task"] = task
            break
    return sample


def _context_extend(sample: dict, pool: list[dict]) -> dict:
    """Extend context by splicing with a related sample's context."""
    if len(pool) > 1:
        other = random.choice(pool)
        if other.get("agent") and other["agent"] != sample["agent"]:
            sample["context"] = (
                f"{sample['context']} | 上一步：[{other['agent']}] 已完成{other.get('expected_tool', 'unknown')}调用"
            )
    return sample


def _semantic_swap(sample: dict) -> dict:
    """Swap keywords with synonyms or aliases."""
    task = sample["task"]
    for original, aliases in _COMPANY_ALIASES.items():
        if original in task:
            replacement = random.choice(aliases)
            task = task.replace(original, replacement, 1)
            sample["task"] = task
            break
    return sample


if __name__ == "__main__":
    # First ensure seed dataset exists
    if not os.path.exists("seed_dataset.json"):
        from build_seed_dataset import build_seed_dataset
        build_seed_dataset()

    augment_dataset()
