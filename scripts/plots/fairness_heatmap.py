#!/usr/bin/env python3
import argparse
import json
import os

import matplotlib.pyplot as plt
import numpy as np


def load_matrix(path: str):
    with open(path, 'r') as f:
        data = json.load(f)
    # Expect a dict: {"labels": [...], "matrix": [[...]]}
    labels = data['labels']
    mat = np.array(data['matrix'], dtype=float)
    return labels, mat


def plot_heatmap(labels, mat, output: str):
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(mat, cmap='YlGnBu', aspect='auto')
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_yticklabels(labels)
    ax.set_title('Fairness / Sensitivity Heatmap')
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel('Score', rotation=90)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='JSON with labels and matrix')
    parser.add_argument('--output', required=True, help='Output image path')
    args = parser.parse_args()

    labels, mat = load_matrix(args.input)
    plot_heatmap(labels, mat, args.output)


if __name__ == '__main__':
    main()


