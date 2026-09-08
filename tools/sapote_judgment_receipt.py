#!/usr/bin/env python3
"""
sapote_judgment_receipt.py — write-back artifact that makes gold_completeness verifiable.

Mamey leaves gold_completeness = JUDGMENT_PENDING after extraction; the Sapote/LLM layer is
supposed to flip it once judgment is done, but nothing recorded that. This emits a
sapote_judgment_receipt.json that pins down what the judgment layer actually produced:
Mode B card count vs raw BGC count, the deliverable-suite check result, and the standing
safety flags. gold_completeness flips to COMPLETE only when every BGC has a Mode B card AND
the deliverable suite passes. Fails closed.

Relationship to the W9 structure gate (v9.7.150+):

  This tool answers "how many Mode B cards exist?" — a *presence* check.
  `mamey.modeb_structure_gate.lint_card` answers "is this card structurally
  valid against the §1–§30 contract?" — a *structure* check. They are
  complementary, not redundant.

  The PRE-W9 implementation counted cards by a regex matching only the
  legacy `## BGC001` heading pattern. After W9 the canonical card title is
  `# Mode B — BGC033 (NODE_7) — AS-XXX` and section headings are `## §1
  Identity and node/region` (etc.) — neither matches the legacy regex.
  Result: a structurally-valid W9 card was not counted at all, so the
  receipt would emit JUDGMENT_PENDING even when every BGC had a real card
  on disk. This was the bunny-hop audit's flagged conflict.

  Post-fix (v9.7.151+):
    1. The preferred canonical path is `--register <pkg>`, which reads
       `<strain>_judgment_register.json` directly. The register's
       `complete_bgcs` field is the source of truth.
    2. The legacy `--modeb <glob>` path remains, with the regex extended
       to also match the W9 forms: the `<!-- MODE B: <BGC_ID> | ... -->`
       header that `record_mode_b` writes, and the `# Mode B — <BGC_ID>`
       title that the W9 template emitter writes.
    3. If both `--register` and `--modeb` are supplied, the register wins.

Usage:
  # Canonical post-W9 flow:
  python tools/sapote_judgment_receipt.py \
      --package runs/<strain>/package \
      --register runs/<strain>/package \
      --manifest DELIVERABLE_MANIFEST_<strain>.md \
      [--mode gold] [--out sapote_judgment_receipt.json]

  # Legacy file-glob flow (back-compat):
  python tools/sapote_judgment_receipt.py \
      --package runs/<strain>/package \
      --manifest DELIVERABLE_MANIFEST_<strain>.md \
      --modeb path/to/ModeB_*.md [more ...]

Exit 0 = COMPLETE, 1 = JUDGMENT_PENDING.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, json, os, re, subprocess, sys, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_dump_json

SUITE_CHECK_TIMEOUT_SECONDS = 120


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# Regex matches three card-heading conventions, oldest to newest:
#   (a) legacy `## BGC001` style       (pre-v9.7.144)
#   (b) W9 HTML header `<!-- MODE B: BGC001 | strain: ... | session: ... -->`
#       — written by mamey.judgment_store.record_mode_b at the top of every
#         card it persists
#   (c) W9 template emitter title `# Mode B — BGC033 (NODE_7) — AS-XXX`
#       — written by mamey.modeb_template_emitter.emit_card_template
# Counts unique BGC IDs across all matches (a single card with both a
# header (b) and a title (c) is one card, not two).
_CARD_PATTERNS = [
    # (a) legacy heading
    re.compile(r'^#+\s*BGC\s*(\d+)|^\s*###\s*BGC\[?(\d+)', re.M),
    # (b) W9 header comment
    re.compile(r'<!--\s*MODE\s*B:\s*BGC(\d+)', re.M | re.I),
    # (c) W9 template title
    re.compile(r'^#\s*Mode\s*B\s*[\u2014\-]\s*BGC(\d+)', re.M | re.I),
]


def _structure_linter():
    """Load the mandatory structure gate for completeness-sensitive counting."""
    from mamey.modeb_structure_gate import lint_card
    return lint_card


def count_modeb_cards(paths, enforce_structure=False):
    """Count unique BGC IDs across all matched files. Handles legacy and
    W9 card formats (see _CARD_PATTERNS above). The unique-ID semantics
    avoid double-counting a single card that carries both the W9 header
    and the W9 title.

    wishlist #1 (v9.7.206): a structurally-invalid card (fails the §1–§30 structure
    gate) must NOT count toward gold_completeness — otherwise a card that passes the
    count check but fails `lint_card` can flip COMPLETE. Mirrors compilation_gate's
    fail-open ERROR filter (a gate import/parse failure never crashes the count)."""
    _lint = None
    if enforce_structure:
        try:
            _lint = _structure_linter()
        except Exception as exc:
            raise RuntimeError(
                "Mode B structure gate unavailable; refusing completeness credit"
            ) from exc
    seen_bgc_ids = set()
    for p in paths:
        for f in glob.glob(p):
            try:
                txt = open(f, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if _lint is not None:
                try:
                    if sum(1 for x in _lint(txt, bgc_context=None) if x.get("severity") == "ERROR"):
                        continue  # structurally-invalid card — do not count it as present
                except Exception as exc:
                    raise RuntimeError(
                        f"Mode B structure gate failed for {f}; refusing completeness credit"
                    ) from exc
            for pat in _CARD_PATTERNS:
                for m in pat.finditer(txt):
                    bgc_num = next((g for g in m.groups() if g), None)
                    if bgc_num:
                        seen_bgc_ids.add(int(bgc_num))
    return len(seen_bgc_ids)


def cards_from_register(package_dir):
    """Read the judgment register and return (cards_complete, total_bgcs).

    The register is the canonical post-W9 source of truth: `record_mode_b`
    flips per-BGC status to COMPLETE only after the card has been written
    and stamped. Returns (None, None) if no register can be found.
    """
    pkg = package_dir
    candidates = []
    if os.path.isdir(pkg):
        candidates.extend(glob.glob(os.path.join(pkg, "*_judgment_register.json")))
    elif os.path.isfile(pkg) and pkg.endswith("_judgment_register.json"):
        candidates.append(pkg)
    if not candidates:
        return None, None
    try:
        reg = _read_json(candidates[0], encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        return None, None
    return reg.get("complete_bgcs"), reg.get("total_bgcs")


def raw_bgc_count(package):
    man = os.path.join(package, "manifest.json")
    if os.path.exists(man):
        m = _read_json(man)
        bc = m.get("bgc_counts") or {}
        return bc.get("raw") or m.get("raw_bgcs") or len(m.get("bgcs", []))
    return None

def suite_pass(manifest, mode, here):
    chk = os.path.join(here, "check_deliverable_suite.py")
    if not (manifest and os.path.exists(manifest) and os.path.exists(chk)):
        return None, "deliverable-suite check not run (manifest or checker absent)"
    try:
        r = subprocess.run(
            [sys.executable, chk, "--manifest", manifest, "--mode", mode, "--json"],
            capture_output=True, text=True, timeout=SUITE_CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return None, f"deliverable-suite check timed out after {SUITE_CHECK_TIMEOUT_SECONDS} seconds"
    except OSError as exc:
        return None, f"deliverable-suite check could not start: {exc}"
    try:
        j = json.loads(r.stdout)
        return j.get("pass"), j.get("findings", [])
    except Exception:
        return None, r.stdout[-200:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--register", default=None,
                    help="Path to the package dir or its <strain>_judgment_register.json. "
                         "When supplied, the register's complete_bgcs is the canonical "
                         "card count (W9+, v9.7.151). Wins over --modeb if both given.")
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--modeb", nargs="*", default=[],
                    help="Legacy file-glob flow. Counts cards by regex across the matched "
                         "files. The regex now handles legacy headings, W9 HTML headers, "
                         "and W9 template titles (v9.7.151). Use --register for the "
                         "canonical post-W9 path.")
    ap.add_argument("--mode", default="gold", choices=["smoke", "standard", "gold"])
    ap.add_argument("--out", default="sapote_judgment_receipt.json")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))

    raw = raw_bgc_count(a.package)

    # Card-count source priority: --register (canonical) > --modeb (legacy)
    card_source = None
    cards = 0
    register_complete = None
    register_total = None
    card_validation_error = None
    if a.register:
        register_complete, register_total = cards_from_register(a.register)
        if register_complete is not None:
            cards = register_complete
            card_source = "judgment_register"
    if card_source is None and a.modeb:
        try:
            cards = count_modeb_cards(a.modeb, enforce_structure=True)
            card_source = "file_glob_regex"
        except RuntimeError as exc:
            cards = 0
            card_source = "file_glob_structure_gate_error"
            card_validation_error = str(exc)
    if card_source is None:
        # Neither path supplied → fall back to nothing; downstream check
        # will report 0/N which is JUDGMENT_PENDING (correct fail-closed).
        card_source = "none"

    spass, sfind = suite_pass(a.manifest, a.mode, here)

    modeb_complete = (raw is not None and cards >= raw)
    # v9.7.374 (audit lane): `(not gold or modeb_complete)` was dead — `modeb_complete` is
    # already required by the first AND operand, so by the time this third clause is evaluated
    # `modeb_complete` is always True, making `not gold or modeb_complete` always True too,
    # regardless of `a.mode`. Live-confirmed: `--mode gold` and `--mode smoke` against the same
    # incomplete package produced byte-identical JUDGMENT_PENDING receipts — the `mode`-conditional
    # completion criterion the shape of this line implies (looser completion bar for non-gold
    # modes) never actually took effect. Simplified to the formula this line was already always
    # equivalent to, so the code no longer implies a mode-dependent completion rule it doesn't
    # have. Every current mode requires full Mode B coverage before COMPLETE either way (CLAUDE.md:
    # `standard` is aliased to `gold`, `smoke` is retired at the engine's own `--mode` gate), so
    # this changes no observed behavior, only removes a misleading no-op.
    complete = modeb_complete and (spass is True)
    receipt = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "package": a.package,
        "mode": a.mode,
        "raw_bgcs": raw,
        "modeb_cards_written": cards,
        "modeb_card_source": card_source,
        "modeb_card_validation_error": card_validation_error,
        "register_complete_bgcs": register_complete,
        "register_total_bgcs": register_total,
        "modeb_complete": modeb_complete,
        "deliverable_suite_pass": spass,
        "deliverable_suite_findings": sfind if spass is not True else [],
        "gold_completeness": "COMPLETE" if complete else "JUDGMENT_PENDING",
    }
    atomic_dump_json(receipt, a.out, indent=2)
    emit(json.dumps(receipt, indent=2), f"\n→ wrote {a.out} · gold_completeness = {receipt['gold_completeness']}", sep="\n")
    sys.exit(0 if complete else 1)

if __name__ == "__main__":
    main()
