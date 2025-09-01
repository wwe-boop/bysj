#!/usr/bin/env python3
import argparse
import json
import os
from typing import Dict, Any

import matplotlib.pyplot as plt
import numpy as np


def load_results(path: str) -> Dict[str, Any]:
    with open(path, 'r') as f:
        return json.load(f)


def plot_qoe_metrics(results: Dict[str, Any], output: str) -> None:
    methods = list(results.keys())
    avg_qoe = [results[m]['qoe']['mean'] for m in methods]
    qoe_ci = [results[m]['qoe'].get('ci95', 0.0) for m in methods]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(methods))
    ax.bar(x, avg_qoe, yerr=qoe_ci, capsize=4, color='#4C78A8')
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=20, ha='right')
    ax.set_ylabel('Average QoE')
    ax.set_title('QoE Comparison')
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='JSON results file with QoE metrics')
    parser.add_argument('--output', required=True, help='Output image path (e.g., docs/assets/qoe_comparison.png)')
    args = parser.parse_args()

    results = load_results(args.input)
    plot_qoe_metrics(results, args.output)


if __name__ == '__main__':
    main()


