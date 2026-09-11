"""Generate deterministic, synthetic figure assets for renderer evaluation."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"


def evidence_summary(assets: Path = ASSETS) -> None:
    labels = ["Inventory", "Domains", "Comparators", "Context", "Claim gate"]
    values = [1.0, 0.82, 0.58, 0.74, 0.66]
    colors = ["#0B8793", "#0B8793", "#E6A623", "#0B8793", "#D45B42"]
    fig, ax = plt.subplots(figsize=(8.2, 3.7), dpi=180)
    ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.56)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Demonstration evidence-state completeness")
    ax.set_title("Evidence streams remain separate", loc="left", weight="bold", color="#082A45")
    ax.grid(axis="x", color="#D9E2E5", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    for index, value in enumerate(values[::-1]):
        ax.text(value + 0.02, index, f"{value:.2f}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(assets / "evidence_summary.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def phylogeny(assets: Path = ASSETS) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.3), dpi=180)
    ax.axis("off")
    leaves = [("Demo_A", 4.6), ("Demo_B", 3.6), ("Demo_C", 2.4), ("Outgroup", 1.2)]
    segments = [
        ((0.8, 4.1), (2.2, 4.1)), ((0.8, 3.6), (0.8, 4.6)),
        ((2.2, 4.1), (3.7, 4.1)), ((3.7, 4.1), (6.4, 4.6)), ((3.7, 4.1), (6.4, 3.6)),
        ((0.8, 4.1), (0.8, 2.4)), ((0.8, 2.4), (6.4, 2.4)),
        ((0.8, 2.4), (0.8, 1.2)), ((0.8, 1.2), (6.4, 1.2)),
    ]
    for (x1, y1), (x2, y2) in segments:
        ax.plot([x1, x2], [y1, y2], color="#0B8793", linewidth=2)
    for label, y in leaves:
        ax.text(6.55, y, label, va="center", fontsize=10, color="#17242E")
    ax.text(3.85, 4.25, "98", fontsize=8, color="#D45B42")
    ax.text(0.45, 2.9, "71", fontsize=8, color="#D45B42")
    ax.plot([4.8, 5.8], [0.55, 0.55], color="#17242E", linewidth=1.5)
    ax.text(5.3, 0.35, "0.1 substitutions/site", ha="center", fontsize=7, color="#506270")
    ax.set_xlim(0.2, 8.1)
    ax.set_ylim(0.1, 5.1)
    ax.set_title("Synthetic protein-family tree fixture", loc="left", weight="bold", color="#082A45")
    fig.tight_layout()
    fig.savefig(assets / "synthetic_phylogeny.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    """v9.7.412: `--out DIR` renders into DIR instead of the shipped `assets/` (the test suite passes a
    temp dir so a full run never mutates release assets; matplotlib output is not byte-stable across
    environments, and a re-render in place flipped `verify_release_identity` at the .409 seal)."""
    import argparse
    ap = argparse.ArgumentParser(description="Render the synthetic document-rendering fixture images.")
    ap.add_argument("--out", default=None, help="output directory (default: the shipped examples assets dir)")
    args = ap.parse_args(argv)
    assets = Path(args.out) if args.out else ASSETS
    assets.mkdir(parents=True, exist_ok=True)
    evidence_summary(assets)
    phylogeny(assets)


if __name__ == "__main__":
    main()

