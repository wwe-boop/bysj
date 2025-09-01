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


def plot_admission_rates(results: Dict[str, Any], output: str) -> None:
    methods = list(results.keys())
    ar = [results[m]['admission_rate'] for m in methods]
    rr = [results[m]['rejection_rate'] for m in methods]
    dr = [results[m].get('degradation_rate', 0.0) for m in methods]
    labels = methods

    width = 0.25
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x - width, ar, width, label='Admission', color='#72B7B2')
    ax.bar(x, rr, width, label='Rejection', color='#E45756')
    ax.bar(x + width, dr, width, label='Degradation', color='#F58518')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha='right')
    ax.set_ylabel('Rate')
    ax.set_title('Admission / Rejection / Degradation Rates')
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='JSON results with rates')
    parser.add_argument('--output', required=True, help='Output image path')
    args = parser.parse_args()

    results = load_results(args.input)
    plot_admission_rates(results, args.output)


if __name__ == '__main__':
    main()


