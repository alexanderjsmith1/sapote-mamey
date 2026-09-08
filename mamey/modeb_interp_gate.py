"""mamey.modeb_interp_gate — Mode-B INTERPRETATION gate (FA4 prototype, advisory).

Distinct from the existing gates, which all measure FORM:
  * `verify-modeb` (`authored_verify.verify_modeb_command` -> `modeb_structure_gate.lint_card`):
    §1-§48 structure + per-section char/depth floors + evidence-presence.
  * `claim-safety` (`_claim_safety_findings`): keyword hygiene.
This gate measures whether the card makes an interpretive JUDGMENT with SUBSTANCE —
a §4/§19 verdict that is BACKED BY CITED EVIDENCE (a convergence tier, a named alternative,
a resolving experiment, >=2 integrated evidence streams), not merely present.

It is complementary, NOT a duplicate: it never re-checks structure or depth. It is meant to be
wired as `verify-modeb --interp`, which runs the structure gate first (unchanged) and then ADDS
these advisory findings. Standalone it exits 1 on any FAIL (authoring-loop use); as the `--interp`
layer it emits WARN-severity findings so it never changes the structure gate's verdict or any score.

Reconciliation with the engine:
  * Section bodies come from `modeb_structure_gate.extract_section_bodies` (the SAME section view
    `verify-modeb` uses), replacing this tool's original ad-hoc `## §N` regex.
  * The interpretation itself lives in two additive `####` subsections INSIDE §4 (anchors
    `SYNTHESIS` / `REFDARK`) seeded by the template emitter — no `##` heading is added/removed, so
    the structure gate's 25-heading count is unaffected.

Checks (a card PASSES only if all applicable checks pass):
  C1 SYNTHESIS present + substantive (>=350 chars in the block).
  C2 SYNTHESIS cites a convergence TIER token (H1_/.../H5_/CAUTION_/reference-dark).
  C3 SYNTHESIS names a LEADING ALTERNATIVE, and §9 lists >=2 hypotheses.
  C4 SYNTHESIS names a RESOLVING EXPERIMENT (discriminating experiment / §16 / §30).
  C5 >=2 evidence STREAMS integrated (convergence + one of nr/BLASTp/SwissProt/MIBiG/KCB + domain/HMM).
  C6 REFDARK: if the card shows any reference-dark / partial-module signal, a domain-based read
     of that homology-poor core must be present (absence-of-homolog read from domains, not silence).

Modes:
  default  (anchor-optional) — if the #### SYNTHESIS/REFDARK anchor block is absent/thin, fall back
           to the equivalent §-sections (§8 tier, §9 alternatives, §11, §19 judgement, §16/§30
           experiment; §4 prose for reference-dark), so PRE-PATCH interpretive cards score fairly.
  --strict — interpretation MUST live in the anchors (enforces the new format on NEW cards).

CLI:  python -m mamey.modeb_interp_gate <card.md> [<card2.md> ...] [--strict]
Exit 0 if all cards PASS, 1 if any FAIL.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import os
import re
import sys

TIER   = re.compile(r"\b(H[1-5]_[A-Z_]+|CAUTION_[A-Z_]+|reference-dark)\b", re.I)
ALT    = re.compile(r"\b(alternative|competing|two-model|multi-core|cluster-of-clusters|leading alternative)\b", re.I)
EXP    = re.compile(
    r"\b(resolv\w*|resolut\w*|discriminat\w*|HMM|adjudicat\w*|LC-?HRMS|LC-?MS|"
    r"long-read|express\w*|feeding|reciprocal-best|§16|§30)\b", re.I
)
STREAM_CONV = re.compile(r"\b(convergence|H[1-5]_|MIBiG)\b", re.I)
STREAM_HOM  = re.compile(r"\b(nr|BLASTp|Swiss-?Prot|UniProt|KCB|KnownClusterBlast|ClusterBlast)\b", re.I)
STREAM_DOM  = re.compile(r"\b(domain|HMM|module|architecture|grammar|sec_met|smcog|pfam|KS|AT|ACP|PCP)\b")
REFDARK_SIG = re.compile(r"(DATA REQUEST|no current-assembly.*hit|no .*Swiss-?Prot hit|reference-dark|"
                         r"incomplete module|no complete .* module|partial module|degenerate module)", re.I)

# Checks whose failure the --interp layer surfaces as its own advisory codes.
_CODE = {
    "C1 synthesis present+substantive": "INTERP_NO_SYNTHESIS",
    "C2 cites convergence tier":        "INTERP_NO_TIER",
    "C3 names alternative (+§9 >=2)":    "INTERP_NO_ALTERNATIVE",
    "C4 names resolving experiment":     "INTERP_NO_EXPERIMENT",
    "C5 >=2 evidence streams":           "INTERP_THIN_EVIDENCE",
    "C6 reference-dark domain read":     "INTERP_REFDARK_SILENT",
}


def _section_bodies(text):
    """Use the engine's canonical section extractor (the same view verify-modeb uses)."""
    try:
        from .modeb_structure_gate import extract_section_bodies
    except ImportError:  # allow running as a loose script (tests may load by path)
        from modeb_structure_gate import extract_section_bodies  # type: ignore
    return extract_section_bodies(text)


def section(text, num):
    """Body text of §<num> via the engine extractor. `num` is an int section number."""
    return _section_bodies(text).get(int(num), "")


def anchor_block(text, anchor):
    """Text of the #### subsection carrying `INTERP-GATE anchor: <anchor>`, from just after the
    anchor comment up to the next #### / ## heading or the machine gene table (so an anchor block
    is the AUTHOR'S prose, never the table that follows it)."""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.search(rf"INTERP-GATE anchor:\s*{anchor}\b", ln):
            start = i + 1
            break
    if start is None:
        return ""
    out = []
    for ln in lines[start:]:
        if re.match(r"^#### ", ln) or re.match(r"^## ", ln) \
           or re.match(r"^\*\*Gene table\*\*", ln) or re.match(r"^\|", ln):
            break
        out.append(ln)
    return "\n".join(out)


def _strip_comments(s):
    """Drop <!-- ... --> author-guidance comments so an unauthored stub scores as empty."""
    return re.sub(r"<!--.*?-->", "", s or "", flags=re.DOTALL)


def count_hypotheses(s9):
    """Count distinct alternative hypotheses in §9 (inline '(1)(2)' or line-start markers)."""
    n = len(re.findall(r"\(\d\)", s9))
    if n < 2:
        n = len(re.findall(r"^\s*(?:\d[.\)]|- )", s9, re.M))
    if n < 2 and ALT.search(s9):
        n = 2
    return n


def _refdark_prose(text):
    """§4 prose only (drop the machine gene-table rows), for anchor-optional C6."""
    s4 = section(text, 4)
    return "\n".join(ln for ln in s4.splitlines() if not ln.startswith("|"))


def check_card(path, strict=False):
    """Run the six checks on the card file at `path`. Returns (passed, results) where results is
    an ordered dict {check_label: (ok, detail)}. See module docstring for the two modes."""
    with open(path, encoding="utf-8", errors="ignore") as fh:
        text = fh.read()
    return check_card_text(text, strict=strict)


def check_card_text(text, strict=False):
    """Same as check_card but on already-loaded card text (pure/importable)."""
    syn = _strip_comments(anchor_block(text, "SYNTHESIS"))
    refd = _strip_comments(anchor_block(text, "REFDARK"))
    s9 = section(text, 9)
    res = {}
    mode = "anchored"

    if not strict and len(syn.strip()) < 350:
        syn_eval = "\n".join(section(text, s) for s in (8, 9, 11, 19, 30))
        mode = "fallback(§8/§9/§11/§19/§30)"
    else:
        syn_eval = syn

    res["C1 synthesis present+substantive"] = (len(syn_eval.strip()) >= 350, f"{len(syn_eval.strip())} chars [{mode}]")
    res["C2 cites convergence tier"] = (bool(TIER.search(syn_eval)), (TIER.search(syn_eval).group(0) if TIER.search(syn_eval) else "none"))
    n_alt = count_hypotheses(s9)
    alt_ok = (bool(ALT.search(syn_eval)) or bool(ALT.search(s9))) and n_alt >= 2
    res["C3 names alternative (+§9 >=2)"] = (alt_ok, f"alt={bool(ALT.search(syn_eval)) or bool(ALT.search(s9))}, §9_hyp={n_alt}")
    res["C4 names resolving experiment"] = (bool(EXP.search(syn_eval)), (EXP.search(syn_eval).group(0) if EXP.search(syn_eval) else "none"))
    streams = sum(bool(rx.search(text)) for rx in (STREAM_CONV, STREAM_HOM, STREAM_DOM))
    res["C5 >=2 evidence streams"] = (streams >= 2, f"{streams}/3 (conv/hom/dom)")
    needs_refdark = bool(REFDARK_SIG.search(text))
    if needs_refdark:
        refd_eval = refd if (strict or len(refd.strip()) >= 150) else _refdark_prose(text)
        ok = len(refd_eval.strip()) >= 150 and bool(STREAM_DOM.search(refd_eval))
        res["C6 reference-dark domain read"] = (ok, f"signal=yes, block={len(refd_eval.strip())}ch, domain-read={bool(STREAM_DOM.search(refd_eval))}")
    else:
        res["C6 reference-dark domain read"] = (True, "n/a (no reference-dark signal)")

    passed = all(v[0] for v in res.values())
    return passed, res


def interp_findings(card_md, strict=False, severity="WARN"):
    """Advisory findings for the `verify-modeb --interp` layer, in the SAME shape as
    modeb_structure_gate findings (severity/code/section/message), so they compose with the
    structure gate's output list. Default severity WARN => the layer is non-blocking and never
    changes verify-modeb's exit code or any score. Returns [] when the card PASSes all checks."""
    passed, res = check_card_text(card_md, strict=strict)
    if passed:
        return []
    out = []
    for label, (ok, detail) in res.items():
        if ok:
            continue
        out.append({
            "severity": severity,
            "code": _CODE.get(label, "INTERP_GAP"),
            "section": 4,
            "message": f"{label} — {detail}. Card is structurally complete but the §4 interpretive "
                       f"synthesis lacks judgment substance (this check is advisory / non-ranking).",
        })
    return out


def main(argv):
    strict = "--strict" in argv
    argv = [a for a in argv if a != "--strict"]
    any_fail = False
    for path in argv:
        if not os.path.isfile(path):
            emit(f"!! not found: {path}"); any_fail = True; continue
        passed, res = check_card(path, strict=strict)
        verdict = "PASS" if passed else "FAIL"
        emit(f"\n{'=' * 70}\n[{verdict}] {os.path.basename(path)}")
        for k, (ok, detail) in res.items():
            emit(f"  {'PASS' if ok else 'FAIL'}  {k:34} — {detail}")
        any_fail = any_fail or not passed
    emit()
    return 1 if any_fail else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        emit(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1:]))
