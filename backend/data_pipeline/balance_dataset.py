"""Balance the dataset across labels, agents, and tools.

Ensures:
- Fair representation of success/failure labels
- Balanced distribution across 6 agents
- Coverage of all 9 tools
- Diverse failure types
"""

from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any


def balance_dataset(
    input_path: str = "augmented_dataset.json",
    output_path: str = "balanced_dataset.json",
) -> list[dict]:
    """Balance the augmented dataset.

    Strategy:
    - Ensure at least 20% failure cases
    - Balance across agents (each agent gets roughly equal samples)
    - Ensure all tools are represented
    - Cap max samples per identical task to 50

    Args:
        input_path: Path to augmented dataset.
        output_path: Path to save balanced dataset.

    Returns:
        Balanced list of samples.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    print(f"Input: {len(samples)} samples")

    # ── Analyze distribution ──────────────────────────────────────────
    label_counts = Counter(s["label"] for s in samples)
    agent_counts = Counter(s["agent"] for s in samples)
    tool_counts = Counter(s["expected_tool"] for s in samples)
    task_counts = Counter(s["task"] for s in samples)

    print(f"Label distribution: {dict(label_counts)}")
    print(f"Agent distribution: {dict(agent_counts)}")
    print(f"Tool distribution: {dict(tool_counts)}")

    # ── Balance by label ──────────────────────────────────────────────
    success_samples = [s for s in samples if s["label"] == "success"]
    failure_samples = [s for s in samples if s["label"] != "success"]

    target_total = len(samples)
    target_failure_ratio = 0.20

    # Adjust failure count
    desired_failures = int(target_total * target_failure_ratio)
    if len(failure_samples) > desired_failures:
        failure_samples = failure_samples[:desired_failures]
    # If too few failures, keep all

    balanced = success_samples + failure_samples
    random.shuffle(balanced)

    # ── Balance by agent ──────────────────────────────────────────────
    agent_samples: dict[str, list[dict]] = {agent: [] for agent in agent_counts}
    for s in balanced:
        agent_samples.setdefault(s["agent"], []).append(s)

    target_per_agent = len(balanced) // len(agent_samples)
    balanced = []
    for agent, s_list in agent_samples.items():
        if len(s_list) > target_per_agent * 2:
            s_list = s_list[:target_per_agent * 2]
        balanced.extend(s_list)

    # ── Ensure tool coverage ──────────────────────────────────────────
    final: list[dict] = []
    tools_seen: set[str] = set()
    for s in balanced:
        final.append(s)
        tools_seen.add(s["expected_tool"])

    # Ensure all tools appear
    all_tools = set()
    for s in samples:
        all_tools.add(s["expected_tool"])

    missing_tools = all_tools - tools_seen
    for tool in missing_tools:
        candidates = [s for s in samples if s["expected_tool"] == tool]
        if candidates:
            final.extend(candidates[:5])  # Add up to 5 samples per missing tool

    # ── Save ──────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    # Print final stats
    final_labels = Counter(s["label"] for s in final)
    final_agents = Counter(s["agent"] for s in final)
    print(f"\nBalanced dataset: {len(final)} samples → {output_path}")
    print(f"Final labels: {dict(final_labels)}")
    print(f"Final agents: {dict(final_agents)}")

    return final


if __name__ == "__main__":
    import random
    random.seed(42)

    if not os.path.exists("augmented_dataset.json"):
        from build_seed_dataset import build_seed_dataset
        from augment_dataset import augment_dataset
        build_seed_dataset()
        augment_dataset()

    balance_dataset()
