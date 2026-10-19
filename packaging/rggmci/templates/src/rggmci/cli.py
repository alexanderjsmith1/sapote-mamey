"""rggmci — surface candidate BGC fragments that may belong to one pathway, from antiSMASH results.

One genome:   rggmci genome.zip --out result.json --pairs pairs.tsv
Many genomes: rggmci zips/ more.zip --out-dir rggmci_results/
BLASTp layer: rggmci fasta genome.zip --out-dir queries/        (then run NCBI BLASTp yourself)
              rggmci blastp-layer --manifest queries/blastp_manifest.json --hits Hit_Table.csv --xml2 r.xml --out-dir layer/
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unicodedata
from pathlib import Path

from . import run
from .csv_safety import SafeDictWriter
from .core import canonical_artifacts, result_summary, SUMMARY_COLUMNS, GROUP_COLUMNS
from .ref_completion import tsv_payload

GROUP_COLS = GROUP_COLUMNS
SUMMARY_COLS = SUMMARY_COLUMNS
COMPLETION_NAMES = ("reference_completion", "split_genes", "partner_contigs")


def _inputs(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out += sorted(x for x in p.rglob("*.zip") if not x.name.startswith("._"))
        else:
            out.append(p)
    return out


def _write_tsv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("xb") as handle:
        handle.write(tsv_payload(rows, cols, fixed_order=True))


def _write_json(path: Path, result: dict) -> None:
    with path.open("x") as fh:
        fh.write(json.dumps(result, indent=1, default=str) + "\n")


def _portable_key(path: Path) -> str:
    # Resolve existing symlinks and normalize names conservatively across Mac/Linux filesystems.
    return unicodedata.normalize("NFC", str(path.resolve())).casefold()


def _within(child: str, parent: str) -> bool:
    return Path(child).is_relative_to(Path(parent))


def _preflight(zips: list[Path], out: Path | None, pairs: Path | None,
               out_dir: Path | None) -> list[Path]:
    """Admit the entire primary-CLI roster without creating files or directories."""
    if len(zips) > 1 and (out is not None or pairs is not None):
        raise ValueError("several inputs: --out and --pairs are single-genome destinations; use --out-dir only")
    if len(zips) > 1 and out_dir is None:
        raise ValueError("several inputs: use --out-dir")
    identities, names, input_keys = set(), set(), set()
    for z in zips:
        info = z.stat()
        identity = (info.st_dev, info.st_ino)
        key = _portable_key(z)
        name = unicodedata.normalize("NFC", z.stem).casefold()
        if identity in identities or key in input_keys:
            raise ValueError(f"duplicate input or physical alias: {z}")
        if name in names:
            raise ValueError(f"input stems collide (case/Unicode insensitive): {z.stem}")
        identities.add(identity)
        input_keys.add(key)
        names.add(name)
    destinations = [p for p in (out, pairs) if p is not None]
    if out_dir is not None:
        if out_dir.is_symlink() or (out_dir.exists() and not out_dir.is_dir()):
            raise ValueError(f"output directory must be an ordinary new or empty directory: {out_dir}")
        if out_dir.exists() and any(out_dir.iterdir()):
            raise ValueError(f"output directory is occupied; choose a new or empty directory: {out_dir}")
        directory_key = _portable_key(out_dir)
        if any(_within(k, directory_key) for k in input_keys):
            raise ValueError(f"output directory contains an input: {out_dir}")
        for z in zips:
            destinations.extend(out_dir / (z.stem + suffix) for suffix in
                                (".json", "_pairs.tsv", "_related_loci.tsv", "_candidate_groups.tsv", "_summary.tsv",
                                 *(f"_{n}.tsv" for n in COMPLETION_NAMES)))
        destinations.extend(out_dir / n for n in ("SUMMARY.tsv", "CANDIDATE_GROUPS.tsv"))
    keys: set[str] = set()
    for path in destinations:
        key = _portable_key(path)
        if any(_within(key, k) or _within(k, key) for k in input_keys):
            raise ValueError(f"output overlaps an input: {path}")
        if any(_within(key, k) or _within(k, key) for k in keys):
            raise ValueError(f"output destinations overlap: {path}")
        if out_dir is not None and _within(_portable_key(out_dir), key):
            raise ValueError(f"output file overlaps output directory: {path}")
        if path.exists() or path.is_symlink():
            raise ValueError(f"output destination is occupied: {path}")
        for parent in path.parents:
            if (parent.exists() or parent.is_symlink()) and not parent.is_dir():
                raise ValueError(f"output parent is not a directory: {parent}")
        keys.add(key)
    return destinations


def _write_completion_tables(block: dict, out_dir: Path, prefix: str) -> None:
    # Reuse the shared formatter in a disposable directory, then publish exclusively.
    # Its ordinary writes must never overwrite a concurrently occupied final destination.
    from .ref_completion import write_tables
    with tempfile.TemporaryDirectory(prefix="rggmci-completion-") as temporary:
        for source in write_tables(block, Path(temporary), prefix):
            with (out_dir / source.name).open("xb") as fh:
                fh.write(source.read_bytes())


def _write_result(result: dict, name: str, out: Path | None, pairs_path: Path | None,
                  out_dir: Path | None) -> None:
    artifacts = canonical_artifacts(result, name=name)
    if out is not None:
        with out.open("xb") as handle:
            handle.write(artifacts[f"{name}.json"])
    if pairs_path is not None:
        with pairs_path.open("xb") as handle:
            handle.write(artifacts[f"{name}_pairs.tsv"])
    if out_dir is not None:
        for filename, payload in artifacts.items():
            with (out_dir / filename).open("xb") as handle:
                handle.write(payload)


def _summary(name: str, res: dict) -> dict:
    return result_summary(name, res)


def fasta_main(argv) -> int:
    from .blastp import emit_fasta
    ap = argparse.ArgumentParser(prog="rggmci fasta", description="Write BLASTp query FASTA for the regions in "
                                 "RG-GMCI candidate pairs, for you to run on NCBI BLASTp and read back with blastp-layer.")
    ap.add_argument("zip", type=Path, help="one antiSMASH result ZIP")
    ap.add_argument("--out-dir", type=Path, required=True, help="an empty or new folder")
    ap.add_argument("--include-moderate", action="store_true", help="also MODERATE pairs (default: HIGH only)")
    ap.add_argument("--per-region", type=int, default=6, help="biosynthetic proteins per region (default 6)")
    ap.add_argument("--edge-genes", type=int, default=0,
                    help="also this many proteins nearest the contig end, of any kind (default 0)")
    ap.add_argument("--proteins-per-file", type=int, default=20)
    a = ap.parse_args(argv)
    if not a.zip.is_file():
        print(f"not found: {a.zip}", file=sys.stderr)
        return 2
    try:
        m = emit_fasta(a.zip, run(a.zip), a.out_dir, proteins_per_file=a.proteins_per_file,
                       confidences=("HIGH", "MODERATE") if a.include_moderate else ("HIGH",),
                       per_region=a.per_region, edge_genes=a.edge_genes)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"{len(m['pairs'])} pairs, {len(m['proteins'])} proteins in {len(m['files'])} FASTA file(s) -> {a.out_dir}. "
          f"See {a.out_dir}/HOW_TO_BLASTP.md")
    return 0


def layer_main(argv) -> int:
    from .blastp import blastp_layer, write_layer
    ap = argparse.ArgumentParser(prog="rggmci blastp-layer", description="Read NCBI BLASTp results for an emitted "
                                 "manifest. The layer sits beside the RG-GMCI confidence and never changes it.")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--hits", type=Path, nargs="*", default=[], help="NCBI Hit Table (CSV) file(s)")
    ap.add_argument("--xml2", type=Path, nargs="*", default=[], help="NCBI Single-file XML2 file(s): adds organism names")
    ap.add_argument("--exclude-organism", action="append", default=[],
                    help="drop hits whose organism contains this text, e.g. the genome's own species (repeatable)")
    ap.add_argument("--top-n", type=int, default=5, help="organisms kept per protein for the shared-organism check")
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args(argv)
    missing = [str(p) for p in [a.manifest, *a.hits, *a.xml2] if not p.is_file()]
    if missing or not (a.hits or a.xml2):
        print(f"not found: {', '.join(missing)}" if missing else "give --hits and/or --xml2", file=sys.stderr)
        return 2
    try:
        layer = blastp_layer(a.manifest, a.hits, a.xml2, top_n=a.top_n, exclude_organisms=a.exclude_organism)
        write_layer(layer, a.out_dir)
    except (OSError, ValueError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    st = [r["blastp_status"] for r in layer["proteins"]]
    print(f"{len(st)} proteins: {st.count('HIT')} with hits, {sum(s.startswith('NO_HITS') for s in st)} no hits, "
          f"{st.count('NOT_IN_RESULTS')} not in the results; {len(layer['pairs'])} pairs -> {a.out_dir}")
    if layer["unmapped_queries"]:
        print(f"{len(layer['unmapped_queries'])} result queries did not match the manifest (renamed headers?); "
              "they were left out", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] in ("--version", "-V"):
        from . import __version__, _provenance
        p = _provenance()
        print(f"rggmci {__version__} (source {p.get('built_from_bundle')}, build {p.get('build')}, "
              f"engine {p.get('engine')})")
        return 0
    if argv and argv[0] == "fasta":
        return fasta_main(argv[1:])
    if argv and argv[0] == "blastp-layer":
        return layer_main(argv[1:])
    if argv and argv[0] == "build-mibig-db":
        from .ref_completion import main as completion_main
        return completion_main(argv, prog="rggmci")
    ap = argparse.ArgumentParser(prog="rggmci", description="Candidate BGC fragments that may belong to one "
                                 "pathway, from antiSMASH results. Candidates only: check each one at gene level.")
    ap.add_argument("inputs", nargs="+", type=Path, help="antiSMASH result ZIP(s), or folders of them")
    ap.add_argument("--out", type=Path, help="one genome: write JSON to a new file")
    ap.add_argument("--pairs", type=Path, help="one genome: write ranked-pair TSV to a new file (header-only if empty)")
    ap.add_argument("--out-dir", type=Path, help="new or empty ordinary directory: per-genome JSON/TSV and SUMMARY.tsv")
    ap.add_argument("--diamond-db", type=Path, help="optional: a DIAMOND database of MIBiG proteins (ids start with the "
                    "MIBiG accession). Adds residue-tiling evidence to pairs; never changes a confidence")
    ap.add_argument("--diamond", type=Path, help="the DIAMOND binary (default: $RGGMCI_DIAMOND, then diamond on PATH)")
    ap.add_argument("--residue-scope", choices=("st_paralog", "all"), default="st_paralog",
                    help="pairs to test: those demoted by the whole-gene paralog gate (default), or all")
    ap.add_argument("--mibig-db", type=Path, help="MIBiG protein database folder from `rggmci build-mibig-db` "
                    "(default: $RGGMCI_MIBIG_DB). With it and DIAMOND or BLAST+, each edge region's MIBiG reference is "
                    "searched across the whole genome: missing and split genes, and tested partner contigs")
    ap.add_argument("--reference-completion", choices=("auto", "off"), default="auto",
                    help="auto (default) runs reference-guided completion when its inputs are found; off skips it. "
                         "Every pair and table says which tier ran")
    ap.add_argument("--sensitivity", choices=("sensitive", "more-sensitive", "ultra-sensitive", "default"),
                    default="sensitive", help="DIAMOND mode for the completion search (default sensitive)")
    ap.add_argument("--threads", type=int, default=4, help="aligner threads (default 4)")
    ap.add_argument("--pfam", type=Path, help="optional pressed Pfam-A.hmm (needs pyhmmer): sets aside a lone partner "
                    "find beside housekeeping genes")
    ap.add_argument("--registry-from", type=Path, help="explicit common asset-registry anchor; default none")
    ap.add_argument("--label", help="logical strain label, single input only; default archive stem")
    ap.add_argument("--residue-work-dir", type=Path)
    ap.add_argument("--completion-work-dir", type=Path)
    a = ap.parse_args(argv)
    residue = {"reference_completion": a.reference_completion, "mibig_db": a.mibig_db, "diamond": a.diamond,
               "sensitivity": a.sensitivity, "threads": a.threads, "pfam_hmm": a.pfam}
    if a.diamond_db:
        residue.update(diamond_db=a.diamond_db, residue_scope=a.residue_scope)
    elif a.residue_scope != "st_paralog":
        residue["residue_scope"] = a.residue_scope
    for key, value in (("mibig_db_registry_from", a.registry_from), ("label", a.label),
                       ("residue_work_dir", a.residue_work_dir), ("completion_work_dir", a.completion_work_dir)):
        if value is not None:
            residue[key] = value
    try:
        zips = _inputs(a.inputs)
        if a.label is not None and len(zips) != 1:
            raise ValueError("--label requires exactly one input")
        missing = [z for z in zips if not z.is_file()]
        if missing or not zips:
            raise ValueError(f"not found: {', '.join(map(str, missing)) or 'no .zip inputs'}")
        destinations = _preflight(zips, a.out, a.pairs, a.out_dir)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    try:
        if a.out_dir is not None:
            a.out_dir.mkdir(parents=True, exist_ok=True)
        for path in destinations:
            path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"output error: {exc}", file=sys.stderr)
        return 2
    summary, all_groups = [], []
    for z in zips:
        name = z.stem
        try:
            res = run(z, **residue)
        except Exception as exc:   # report and keep going; one bad ZIP should not stop a batch
            summary.append({"genome": name, "error": f"{type(exc).__name__}: {exc}"[:200]})
            print(f"{z.name}: ERROR {type(exc).__name__}", file=sys.stderr)
            continue
        pairs = res.get("ranked_pairs") or []
        logical = (res.get("input") or {}).get("label", name)
        s = _summary(logical, res)
        summary.append(s)
        for g in res.get("candidate_groups") or []:
            all_groups.append({"genome": logical, **{k: g[k] for k in ("group", "n_regions", "n_contigs", "n_at_contig_ends",
                                                                   "high_pairs")},
                               "regions": "; ".join(f"{r['identity']} [{r['products']}] {r['edge_status']}"
                                                    for r in g["regions"]),
                               "pairs": "; ".join(g["pairs"]),
                               "possible_moderate_links": "; ".join(g["possible_moderate_links"])})
        try:
            _write_result(res, name, a.out, a.pairs, a.out_dir)
        except OSError as exc:
            print(f"output error: {exc}", file=sys.stderr)
            return 2
        print(f"{z.name}: {s['regions']} regions, {s['scored_pairs']} pairs, {s['high']} HIGH "
              f"({s['high_cross_contig']} across contigs), {s['candidate_groups']} candidate groups; "
              f"reference completion {s['completion_tier']}")
    if a.out_dir:
        try:
            _write_tsv(a.out_dir / "SUMMARY.tsv", SUMMARY_COLS, summary)
            _write_tsv(a.out_dir / "CANDIDATE_GROUPS.tsv", GROUP_COLS, all_groups)
        except OSError as exc:
            print(f"output error: {exc}", file=sys.stderr)
            return 2
    return 1 if any(s.get("error") for s in summary) else 0
