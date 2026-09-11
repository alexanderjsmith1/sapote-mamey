"""Source-bound Q-020 KCB cumulative-score cohort-tertile figure."""
from __future__ import annotations

import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
from pathlib import Path
from typing import Any

from mamey.exclusions import governed_denominator
from mamey.figure_save import save_figure


class KcbTertileRefusal(RuntimeError):
    """Typed refusal when the governed source contract is incomplete."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def render_kcb_tertiles(owner_inputs: str | Path, outdir: str | Path) -> dict[str, Any]:
    import matplotlib.pyplot as plt
    import numpy as np
    root = Path(owner_inputs).resolve()
    destination = Path(outdir).resolve()
    if destination.exists():
        raise KcbTertileRefusal("G03_OUTPUT_EXISTS")
    input_receipt_path = root / "FIGURE_INPUT_RECEIPT.json"
    if not input_receipt_path.is_file():
        raise KcbTertileRefusal("G03_INPUT_RECEIPT_MISSING")
    input_receipt = json.loads(input_receipt_path.read_text(encoding="utf-8"))
    table = root / "a9_kcb_scores.csv"
    bound = {row["path"]: row for row in input_receipt.get("outputs") or []}.get(table.name)
    if not table.is_file() or not bound or bound.get("sha256") != _sha(table):
        raise KcbTertileRefusal("G03_INPUT_BINDING_FAILED")
    official = governed_denominator()
    study_n = int(input_receipt.get("study_denominator") or 0)
    if not official or int(official.get("strains") or 0) != study_n:
        raise KcbTertileRefusal(
            f"G03_GOVERNED_DENOMINATOR_UNBOUND: selected={study_n} official={official.get('strains') if official else 'MISSING'}"
        )
    rows = _rows(table)
    if any(not row.get("complete_identity") for row in rows):
        raise KcbTertileRefusal("G03_COMPLETE_BGC_IDENTITY_MISSING")
    total = len(rows)
    admitted = []
    for row in rows:
        raw = (row.get("kcb_score") or "").strip()
        if not raw:
            continue
        try:
            score = float(raw)
        except ValueError as exc:
            raise KcbTertileRefusal("G03_KCB_SCORE_INVALID") from exc
        if not row.get("antismash_version"):
            raise KcbTertileRefusal("G03_ANTISMASH_VERSION_UNBOUND")
        admitted.append((row, score))
    if not admitted:
        raise KcbTertileRefusal("G03_NO_ADMITTED_SCORES")
    scores = np.asarray([score for _, score in admitted], dtype=float)
    q33, q66 = np.percentile(scores, [33, 66])
    labels = ("lower cohort third", "middle cohort third", "upper cohort third")
    plotted = []
    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    fallback_label = "derived (clusterblast-only), MEDIUM ceiling"
    for index, (row, score) in enumerate(admitted):
        band = 0 if score < q33 else (1 if score < q66 else 2)
        fallback = (row.get("needs_manual_kcb_check") or "").lower() == "yes"
        ax.scatter(band + (index % 7 - 3) * 0.025, score, s=38,
                   facecolors="none" if fallback else "#0072B2", edgecolors="#D55E00" if fallback else "#0072B2",
                   label=fallback_label if fallback else "KnownClusterBlast rank-1")
        plotted.append({**row, "score": score, "cohort_tertile": labels[band],
                        "fallback_marker": fallback_label if fallback else "filled KnownClusterBlast marker",
                        "q33": q33, "q66": q66})
    handles, legend_labels = ax.get_legend_handles_labels()
    unique = dict(zip(legend_labels, handles))
    ax.legend(unique.values(), unique.keys(), frameon=False)
    ax.set_xticks(range(3), labels)
    ax.set_ylabel("Unnormalized cumulative BLAST score")
    ax.set_title("KnownClusterBlast score distribution — cohort-derived tertile bands")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(rect=(0.05, 0.15, 0.98, 0.94))
    destination.mkdir(parents=True)
    data = destination / "Q020_G03.csv"
    with data.open("w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=list(plotted[0]))
        writer.writeheader(); writer.writerows(plotted)
    caption = destination / "Q020_G03.caption.md"
    versions = sorted({row["antismash_version"] for row, _ in admitted})
    caption.write_text(
        "# Q020 G03 caption\n\n"
        f"KnownClusterBlast cumulative-score distribution: {len(admitted)} admitted scores / {total} governed BGC rows; "
        f"antiSMASH version(s): {', '.join(versions)}. Bands are cohort-derived 33rd/66th percentile tertiles, not biological thresholds. "
        "Source: `Cumulative BLAST score` in the rank-1 KnownClusterBlast TXT block. Units are an unnormalized cumulative sum that grows with cluster size and match count. "
        "Hollow markers are derived (clusterblast-only), MEDIUM ceiling. Similarity is not identity; capacity is not production or activity.\n",
        encoding="utf-8",
    )
    figure_receipt = save_figure(
        fig, figure_id="Q020_G03", out_stem=destination / "Q020_G03", renderer=__name__,
        package_dir=destination, provenance="KnownClusterBlast rank-1 cumulative score; governed cohort",
    )
    plt.close(fig)
    result = {"schema_version": "sapote-mamey.kcb-tertile-figure.v1", "status": "CANDIDATE_RENDERED",
              "binding_state": "BOUND", "figure_id": "Q020_G03", "governed_strains": study_n,
              "denominator": {"admitted_scores": len(admitted), "total_governed_bgc_rows": total},
              "tertiles": {"q33": float(q33), "q66": float(q66)}, "antismash_versions": versions,
              "data_sha256": _sha(data), "caption_sha256": _sha(caption), "figure_receipt": figure_receipt}
    (destination / "Q020_G03_RECEIPT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
