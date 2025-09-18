#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import os
import argparse
import numpy as np
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA, TruncatedSVD, KernelPCA
from sklearn.random_projection import GaussianRandomProjection
import umap
import datetime

from dd.core import embed


def reduce_embeddings(embeddings, method="PCA", n_components=2):
    if method == "PCA":
        reducer = PCA(n_components=n_components)
    elif method == "KernelPCA":
        reducer = KernelPCA(n_components=n_components, kernel='rbf')
    elif method == "TruncatedSVD":
        reducer = TruncatedSVD(n_components=n_components)
    elif method == "GaussianRandomProjection":
        reducer = GaussianRandomProjection(n_components=n_components)
    elif method == "UMAP":
        reducer = umap.UMAP(n_components=n_components)
    else:
        raise ValueError(f"Unsupported reduction method: {method}")
    
    return reducer.fit_transform(embeddings)


def plot_embeddings(reduced_dict, method, out_dir):
    plt.figure(figsize=(10, 8))
    for label, data in reduced_dict.items():
        plt.scatter(data[:, 0], data[:, 1], alpha=0.6, label=label)
    plt.legend()
    plt.title(f"{method} Projection of Embeddings")
    plt.grid(True)

    os.makedirs(out_dir, exist_ok=True)
    save_path = os.path.join(out_dir, f"embedding_plot_{method}.png")
    plt.savefig(save_path)
    plt.close()
    print(f"[PLOT] Saved to {save_path}")


def write_report(embedding_dict, out_path):
    folders = list(embedding_dict.keys())
    n = len(folders)
    with open(out_path, 'w') as f:
        f.write(f"# Embedding Comparison Report\n\n")
        f.write(f"Generated: {datetime.datetime.now()}\n\n")
        for i in range(n):
            for j in range(i + 1, n):
                f1, f2 = folders[i], folders[j]
                emb1, emb2 = embedding_dict[f1]["embeddings"], embedding_dict[f2]["embeddings"]
                mean1, mean2 = np.mean(emb1, axis=0), np.mean(emb2, axis=0)
                dist = np.linalg.norm(mean1 - mean2)
                f.write(f"## {f1} vs {f2}\n")
                f.write(f"- Centroid distance: **{dist:.4f}**\n\n")
    print(f"[REPORT] Saved report to {out_path}")


def run(folders, dim_reduction_method, output_dir):
    # Embed all folders
    embed_folders = embed.run
    embedding_dict = embed_folders(folders)

    # Reduce and plot
    reduced = {}
    for folder, content in embedding_dict.items():
        reduced[folder] = reduce_embeddings(content["embeddings"], method=dim_reduction_method)

    plot_embeddings(reduced, dim_reduction_method, output_dir)

    # Save report
    report_path = os.path.join(output_dir, "comparison_report.md")
    write_report(embedding_dict, report_path)


if __name__ == "__main__":
    main()