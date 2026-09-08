#!/usr/bin/env python3
"""sync_version.py — propagate the single source-of-truth version into restated files.

WHY THIS EXISTS
---------------
A "version string" is a fact ("this bundle is 9.7.22"). The moment that fact is
copied by hand into more than one file, the copies drift. This bundle shipped with
TAG saying 9.7.6, the session manifest saying 9.7.21, and CITATION saying 9.7.22 —
three answers to one question. The fix is the oldest rule in software: keep the fact
in ONE place and GENERATE every restatement from it.

SOURCE OF TRUTH  ->  pyproject.toml
  [project] version            = ENGINE version (Mamey; what `pip install` produces)
  [tool.sapote] bundle_version = BUNDLE version (the curated Sapote-Mamey release)

FILES THIS SCRIPT REWRITES (pure restatements — safe to machine-generate):
  TAG, SESSION_START_MANIFEST.md (header line), CITATION.cff, RELEASE_MANIFEST.md

FILES IT DOES NOT TOUCH (human-authored; only the test CHECKS them):
  CHANGELOG.md — its newest entry header must already match bundle_version.

It rewrites ANCHORED lines only, so a historical note like "the v9.7.7 RiQ layer"
is never clobbered.

USAGE (run from the bundle root):
  python3 tools/sync_version.py            # rewrite restated files in place
  python3 tools/sync_version.py --check    # exit 1 if anything is out of sync; no writes
"""
import re
import sys
import pathlib
import argparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _wbio import atomic_write_text  # v9.7.405: every version-file write is atomic (CODEX_390 third-gate hardening)


def read_truth():
    """Pull the two version numbers out of pyproject.toml with a tiny regex parse
    (no tomllib dependency, so this runs on Python 3.10+)."""
    txt = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    eng = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', txt)
    bnd = re.search(r'(?m)^\s*bundle_version\s*=\s*"([^"]+)"', txt)
    if not eng:
        sys.exit("pyproject.toml: [project] version not found")
    if not bnd:
        sys.exit("pyproject.toml: [tool.sapote] bundle_version not found")
    return eng.group(1), bnd.group(1)


ENGINE, BUNDLE = read_truth()

def read_stamp() -> str:
    """Read the build stamp from BUILD_STAMP.txt (format: 'build=20260617i')."""
    try:
        txt = (ROOT / "BUILD_STAMP.txt").read_text(encoding="utf-8")
        m = re.search(r"build=(\w+)", txt)
        return m.group(1) if m else ""
    except FileNotFoundError:
        return ""

STAMP = read_stamp()

# F3 (v9.7.247): the release date, derived from the SAME stamp everything else uses, so it cannot rot.
# `date-released` had no rule at all: `sync_version --check` passed while the field sat 24 cuts stale.
_STAMP_DATE = f"{STAMP[0:4]}-{STAMP[4:6]}-{STAMP[6:8]}" if len(STAMP) >= 8 and STAMP[:8].isdigit() else ""

# (relative path, anchored pattern, replacement). Each pattern matches exactly the
# restatement of the version — never a "introduced in vX" historical reference.
RULES = [
    ("wiki/_Sidebar.md", re.compile(r"bundle v\d+(?:\.\d+)* · engine \d+(?:\.\d+)*"), f"bundle v{BUNDLE} · engine {ENGINE}"),
    ("BUILD_STAMP.txt", re.compile(r"(?m)^engine=[^\r\n]+$"), f"engine={ENGINE}"),
    # AUDIT v9.7.95 follow-up (freshness-probe drift, caught by the in-tier gate at the v9.7.96 cut):
    # CHATGPT_START_HERE.md restates bundle/engine/build as a per-release freshness probe that a test
    # (test_chatgpt_start_here_current) asserts is current — but the file was never under sync coverage,
    # so each bump it silently rotted and only the test caught it. These three rules cover its three
    # probe formats (the §0 line, the §3 header, and the colophon) so --apply keeps them current.
    ("CHATGPT_START_HERE.md",
     re.compile(r"v\d+(?:\.\d+)*[a-z]* / \d+(?:\.\d+)*[a-z]* \u00b7 build \w+"),
     f"v{BUNDLE} / {ENGINE} \u00b7 build {STAMP}"),
    ("CHATGPT_START_HERE.md",
     re.compile(r"THIS build \(v\d+(?:\.\d+)*[a-z]* / \d+(?:\.\d+)*[a-z]* \u00b7 \w+\)"),
     f"THIS build (v{BUNDLE} / {ENGINE} \u00b7 {STAMP})"),
    ("CHATGPT_START_HERE.md",
     re.compile(r"v\d+(?:\.\d+)*[a-z]* / engine \d+(?:\.\d+)*[a-z]* \u00b7 build \w+"),
     f"v{BUNDLE} / engine {ENGINE} \u00b7 build {STAMP}"),
    # AUDIT v9.7.95 follow-up (BUNDLE_VERSION drift, caught by test chat): mamey/__init__.py carries
    # both the engine __version__ and the bundle BUNDLE_VERSION, the latter consumed at cli.py to NAME
    # output package zips. BUNDLE_VERSION had silently drifted to 9.7.91 (packages mislabeled) because
    # nothing guarded it. These two rules put both under sync coverage so --check fails on any drift.
    ("mamey/__init__.py",
     re.compile(r'__version__ = "\d+(?:\.\d+)*[a-z]*"'),
     f'__version__ = "{ENGINE}"'),
    ("mamey/__init__.py",
     re.compile(r'BUNDLE_VERSION = "\d+(?:\.\d+)*[a-z]*"'),
     f'BUNDLE_VERSION = "{BUNDLE}"'),
    # Cross-assistant bootstrap files restate bundle/engine/build as first-contact freshness probes.
    ("000_READ_ME_FIRST_CHATGPT_CLAUDE.md",
     re.compile(r"v\d+(?:\.\d+)*[a-z]* · Mamey engine \d+(?:\.\d+)*[a-z]* · build \w+"),
     f"v{BUNDLE} · Mamey engine {ENGINE} · build {STAMP}"),
    ("CHATGPT_READ_ME_FIRST.md",
     re.compile(r"v\d+(?:\.\d+)*[a-z]* / engine \d+(?:\.\d+)*[a-z]* · build \w+"),
     f"v{BUNDLE} / engine {ENGINE} · build {STAMP}"),
    ("CHATGTP_READ_ME_FIRST.md",
     re.compile(r"v\d+(?:\.\d+)*[a-z]* / engine \d+(?:\.\d+)*[a-z]* · build \w+"),
     f"v{BUNDLE} / engine {ENGINE} · build {STAMP}"),
    ("CLAUDE_START_HERE.md",
     re.compile(r"v\d+(?:\.\d+)*[a-z]* · Mamey engine \d+(?:\.\d+)*[a-z]* · build \w+"),
     f"v{BUNDLE} · Mamey engine {ENGINE} · build {STAMP}"),
    ("README.md",
     re.compile(r"Current bundle: v\d+(?:\.\d+)*[a-z]* / engine \d+(?:\.\d+)*[a-z]* · build \w+"),
     f"Current bundle: v{BUNDLE} / engine {ENGINE} · build {STAMP}"),
    # CANDIDATE_251 (v9.7.371): CURRENT_DOCS_INDEX.md is the authority every session is pointed at,
    # yet its header froze THREE times (v9.7.136, v9.7.337, v9.7.367 — each caught by hand, cuts
    # later). The v9.7.367 changelog *claimed* this rule existed ("owned by sync_version"); it did
    # not — the classic green-gate-over-an-unowned-field trap (same class as the TAG build: miss at
    # v9.7.153 and date-released at v9.7.247). Now it is real: --apply re-stamps the header,
    # --check fails on a fourth freeze at build time instead of sealing it.
    ("CURRENT_DOCS_INDEX.md",
     re.compile(r"(?m)^# Current Docs Index — v\d+(?:\.\d+)*[a-z]* · engine \d+(?:\.\d+)*[a-z]* · build \w+"),
     f"# Current Docs Index — v{BUNDLE} · engine {ENGINE} · build {STAMP}"),
    ("TAG",
     re.compile(r"(?m)^sapote-mamey v\d+(?:\.\d+)*[a-z]*"),
     f"sapote-mamey v{BUNDLE}"),
    ("TAG",
     re.compile(r"(?m)^engine: mamey v\d+(?:\.\d+)*[a-z]*"),
     f"engine: mamey v{ENGINE}"),
    # v9.7.159: TAG's `build:` line had NO sync rule — the exact §80 CUT_PROTOCOL trap. It went
    # stale at the v9.7.153 cut (and again at the v9.7.159 freeze) while `sync_version --check`
    # reported OK, because nothing under coverage restated the build stamp on TAG. This rule closes
    # the blind spot: --apply keeps it current, --check now flags its drift.
    ("TAG",
     re.compile(r"(?m)^build: \w+"),
     f"build: {STAMP}"),
    ("SESSION_START_MANIFEST.md",
     re.compile(r"Engine: Mamey v\d+(?:\.\d+)*[a-z]* · Bundle: sapote-mamey-v\d+(?:\.\d+)*[a-z]*"),
     f"Engine: Mamey v{ENGINE} · Bundle: sapote-mamey-v{BUNDLE}"),
    ("CITATION.cff",
     re.compile(r"(?m)^version:\s*\d+(?:\.\d+)*[a-z]*"),
     f"version: {BUNDLE}"),
    # F3 (v9.7.247): `date-released` had no rule, so `sync_version --check` passed while the field sat
    # 24 cuts / 17 days stale. Same class as the TAG `build:` miss documented at v9.7.153: a green gate
    # over a field nobody owns. Derived from BUILD_STAMP.txt's `build=YYYYMMDD...` date.
    ("CITATION.cff",
     re.compile(r'(?m)^date-released:\s*"?\d{4}-\d{2}-\d{2}"?'),
     f'date-released: "{_STAMP_DATE}"'),

    ("RELEASE_MANIFEST.md",
     re.compile(r"(?m)^# Sapote-Mamey Bundle Release Manifest — v\d+(?:\.\d+)*[a-z]*"),
     f"# Sapote-Mamey Bundle Release Manifest — v{BUNDLE}"),
    ("RELEASE_MANIFEST.md",
     re.compile(r"\*\*Bundle version:\*\* `sapote-mamey-v\d+(?:\.\d+)*[a-z]*`"),
     f"**Bundle version:** `sapote-mamey-v{BUNDLE}`"),
    # --- user-facing docs/prompts the critique flagged as stale (2026-06-13) ---
    # README "Bundle:" line restates the BUNDLE version (only current-version mention in this file).
    ("README_START_HERE.md",
     re.compile(r"sapote-mamey-v\d+(?:\.\d+)*[a-z]*"),
     f"sapote-mamey-v{BUNDLE}"),
    # Standalone ChatGPT docs restate the ENGINE version ("Mamey v1.9.x"); all mentions are current.
    ("docs/standalone/MAMEY_STANDALONE_CHATGPT_README.md",
     re.compile(r"Mamey v\d+(?:\.\d+)*[a-z]*"),
     f"Mamey v{ENGINE}"),
    ("docs/standalone/RUN_MAMEY_IN_CHATGPT.md",
     re.compile(r"Mamey v\d+(?:\.\d+)*[a-z]*"),
     f"Mamey v{ENGINE}"),
    # Co-execution prompt work-order restates the BUNDLE version in three contexts
    # (**Bundle:** vX, Bundle: vX, Sapote-Mamey Bundle vX). Backref preserves each lead-in;
    # historical versions live in separate MAMEY_V*_*.md files and the changelog (untouched).
    ("prompts/SAPOTE_MAMEY_CO_EXECUTION_PROMPT.md",
     re.compile(r"((?:\*\*Bundle:\*\*|Sapote-Mamey Bundle|Bundle:)\s+)v\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>v{BUNDLE}"),
    # RELEASE_MANIFEST footer restates the bundle version in generated text (was stale at v9.5.5);
    # normalize the version, preserve whatever generation date is present.
    # v9.7.154: tier token corrected from PUBLIC_RELEASE -> NOT_FOR_PUBLIC_RELEASE on this CODE-tier
    # artifact (PUBLIC_RELEASE was a false claim on a non-signed CODE cut; see RELEASE_MANIFEST
    # "Known limits" redaction-blocked bullet). The token is captured in \g<2> so the version still
    # syncs; if the tier token is changed again, update this literal AND the footer in lockstep.
    ("RELEASE_MANIFEST.md",
     re.compile(r"(\*Generated: \d{4}-\d{2}-\d{2} \| Sapote-Mamey Bundle )v\d+(?:\.\d+)*[a-z]*( \| NOT_FOR_PUBLIC_RELEASE\*)"),
     rf"\g<1>v{BUNDLE}\g<2>"),
    # RELEASE_MANIFEST engine line and build stamp (v9.7.62: previously unpatched, caused drift).
    ("RELEASE_MANIFEST.md",
     re.compile(r"\*\*Engine:\*\* Mamey v\d+(?:\.\d+)*[a-z]*"),
     f"**Engine:** Mamey v{ENGINE}"),
    ("RELEASE_MANIFEST.md",
     re.compile(r"\*\*Authoritative bundle version:\*\* `\d+(?:\.\d+)*[a-z]?`"),
     f"**Authoritative bundle version:** `{BUNDLE}`"),
    ("RELEASE_MANIFEST.md",
     re.compile(r"\*\*Build stamp:\*\* \w+"),
     f"**Build stamp:** {STAMP}"),
    # PROV-15: the carried-forward historical-snapshot note restates "authoritative for v<bundle>"
    # and had drifted to v9.7.319 while the header/anchor fields above are current. Anchor it to BUNDLE.
    ("RELEASE_MANIFEST.md",
     re.compile(r"authoritative for v\d+(?:\.\d+)*[a-z]*"),
     f"authoritative for v{BUNDLE}"),
    # PLAYBOOK header restates Version + Bundle (was stale at v9.7.6).
    ("PLAYBOOK.md",
     re.compile(r"(\*\*Version:\*\* )v[\d._]+[a-z]*"),
     rf"\g<1>v{BUNDLE}"),
    ("PLAYBOOK.md",
     re.compile(r"(\*\*Bundle:\*\* sapote-mamey-v)[\d._]+[a-z]*"),
     rf"\g<1>{BUNDLE}"),
    # HOW_TO_USE title carries the bundle version (was stale at v9.4).
    ("docs/HOW_TO_USE.md",
     re.compile(r"(# How to Use Sapote-Mamey v)\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>{BUNDLE}"),
    # project_state template bundle_version field (was stale at v9.2-dev).
    ("project_state_template.json",
     re.compile(r'("bundle_version":\s*"sapote-mamey-v)[\w.\-]+(")'),
     rf'\g<1>{BUNDLE}\g<2>'),
    # RELEASE_CHECKLIST footer only ('| Active controller' line); 'added vX' annotations are
    # historical and left untouched.
    ("docs/RELEASE_CHECKLIST_v9.md",
     re.compile(r"(\*Sapote-Mamey Bundle )v\d+(?:\.\d+)*[a-z]*( \| Active controller)"),
     rf"\g<1>v{BUNDLE}\g<2>"),
    # --- GUIDE + RUN_DIAGNOSIS tracked-to-bundle (2026-06-17) ---
    # AUDIT v9.7.95 (P-A1): 01_User_Guide.md was renamed to 01_User_Manual.md. Of the four original
    # User-Guide anchors, only the "(engine X, bundle vY)" prereq phrasing survives in the new manual;
    # the other three ("grounded against ...", the "· v.../engine ...*" banner, and the
    # "it should report ..." line) exist in neither 01_User_Manual.md nor anywhere else in the tree, so
    # they are pruned as dead rules. Retargeting this one anchor restores the sync coverage the rename
    # silently dropped — that gap let the manual ship stale at (engine 1.9.86, bundle v9.7.85).
    ("docs/GUIDE/01_User_Manual.md",
     re.compile(r"\(engine \d+(?:\.\d+)*[a-z]*, bundle v\d+(?:\.\d+)*[a-z]*\)"),
     f"(engine {ENGINE}, bundle v{BUNDLE})"),
    # Encyclopedia HTML banner restates the bundle/engine version (current-version pointer).
    ("docs/GUIDE/03_Technical_Manual_Encyclopedia.html",
     re.compile(r"v\d+(?:\.\d+)*[a-z]* / engine \d+(?:\.\d+)*[a-z]*"),
     f"v{BUNDLE} / engine {ENGINE}"),
    # GUIDE README "Current as of" line (added v9.7.75: was drifting to v9.7.57).
    ("docs/GUIDE/00_README.md",
     re.compile(r"Current as of bundle v\d+(?:\.\d+)*[a-z]* / engine Mamey \d+(?:\.\d+)*[a-z]*"),
     f"Current as of bundle v{BUNDLE} / engine Mamey {ENGINE}"),
    # Quick Guide version header (added v9.7.75: was drifting to v9.4).
    ("docs/GUIDE/02_Quick_Guide.md",
     re.compile(r"\*\*Version:\*\* v\d+(?:\.\d+)*[a-z]* / engine Mamey \d+(?:\.\d+)*[a-z]*"),
     f"**Version:** v{BUNDLE} / engine Mamey {ENGINE}"),
    # The Quick Guide's install block is executable release identity, not historical prose.
    # Keep both the unzip and cd examples on the current CODE archive name, and keep the
    # expected sync-version output aligned with the same engine/bundle sources of truth.
    ("docs/GUIDE/02_Quick_Guide.md",
     re.compile(r"sapote-mamey-v\d+(?:\.\d+)*[a-z]*-CODE-\d+v\d+[a-z]*"),
     f"sapote-mamey-v{BUNDLE}-CODE-{STAMP}"),
    ("docs/GUIDE/02_Quick_Guide.md",
     re.compile(r"(# → engine )\d+(?:\.\d+)*[a-z]*(, bundle )\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>{ENGINE}\g<2>{BUNDLE}"),
    # RUN_DIAGNOSIS prompt states which bundle the ChatGPT side has (current-version pointer).
    ("prompts/RUN_DIAGNOSIS_PROMPT.md",
     re.compile(r"the Sapote\u2013Mamey v\d+(?:\.\d+)*[a-z]* bundle"),
     f"the Sapote\u2013Mamey v{BUNDLE} bundle"),
    # H3 v9.7.58: operational prompts carry the bundle version label in header + footer.
    # These two prompts are pasted directly into LLM sessions and must not carry stale versions.
    ("prompts/CLAUDE_SYSTEM_PROMPT.md",
     re.compile(r"(# (?:Claude|Sapote-Mamey)[^\n]*? \u2014 )v\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>v{BUNDLE}"),
    ("prompts/CLAUDE_SYSTEM_PROMPT.md",
     re.compile(r"Sapote-Mamey Bundle v\d+(?:\.\d+)*[a-z]* \|"),
     f"Sapote-Mamey Bundle v{BUNDLE} |"),
    ("prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md",
     re.compile(r"(# (?:Claude|Sapote-Mamey)[^\n]*? \u2014 )v\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>v{BUNDLE}"),
    ("prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md",
     re.compile(r"Sapote-Mamey Bundle v\d+(?:\.\d+)*[a-z]* \|"),
     f"Sapote-Mamey Bundle v{BUNDLE} |"),
    # v9.7.101 (audit P4/P5): the task-brief template header stamp was uncovered and had
    # drifted to v9.4. Add it to the synced set so it tracks the bundle automatically.
    ("prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md",
     re.compile(r"(# Sapote-Mamey / Mamey Task Brief Template \u2014 )v\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>v{BUNDLE}"),
    # AUDIT v9.7.95 (P-A2): the examples/ exemplar files (layperson / bench / fermentation / citation
    # guides and judgment_18strain/Sapote_Judgment_Pack.md) are no longer shipped in any tier —
    # examples/ is empty across the bundle. Their six version-anchor rules are pruned as dead. If
    # exemplars are restored later, re-add anchors here AND ship the files so --check covers them.
    # --- AUDIT v9.7.96 (P-A3): coverage restored for current-claim lines the v9.7.95 pruning left
    #     uncovered. All target EXISTING files (satisfies test_every_sync_rule_targets_an_existing_file).
    #     Feature-introduction refs ("the v9.7.83+ check") use different phrasing and are NOT matched. ---
    ("docs/GUIDE/01_User_Manual.md",
     re.compile(r"current to bundle v\d+(?:\.\d+)*[a-z]* / engine Mamey \d+(?:\.\d+)*[a-z]*"),
     f"current to bundle v{BUNDLE} / engine Mamey {ENGINE}"),
    # --- AUDIT v9.7.413: the wiki twins of the stamped guides carried the SAME
    #     currency claim with no owner. wiki/User-Manual.md and wiki/Encyclopedia.md state it in a
    #     prose footer, wiki/Concepts-Q-and-A.md capitalises it as a standalone line, and
    #     wiki/Encyclopedia.md's sits MID-SENTENCE -- so the anchored HEADER form the stamp-lock
    #     test matches missed all three, and all three had drifted to v9.7.401 / 1.9.143 (11 cuts).
    #     `[Cc]` covers the capitalised variant; the phrase match is deliberately unanchored so a
    #     mid-sentence claim is still re-stamped. ---
    ("wiki/User-Manual.md",
     re.compile(r"current to bundle v\d+(?:\.\d+)*[a-z]* / engine Mamey \d+(?:\.\d+)*[a-z]*"),
     f"current to bundle v{BUNDLE} / engine Mamey {ENGINE}"),
    # Concepts-Q-and-A carries BOTH cases: a capitalised probe line and a lowercase prose footer.
    # One [Cc] rule with a single replacement would rewrite one of them and never reach a fixed
    # point, so `--check` would report OUT OF SYNC forever. Case-exact rules keep it idempotent.
    ("wiki/Concepts-Q-and-A.md",
     re.compile(r"Current to bundle v\d+(?:\.\d+)*[a-z]* / engine Mamey \d+(?:\.\d+)*[a-z]*"),
     f"Current to bundle v{BUNDLE} / engine Mamey {ENGINE}"),
    ("wiki/Concepts-Q-and-A.md",
     re.compile(r"current to bundle v\d+(?:\.\d+)*[a-z]* / engine Mamey \d+(?:\.\d+)*[a-z]*"),
     f"current to bundle v{BUNDLE} / engine Mamey {ENGINE}"),
    ("wiki/Encyclopedia.md",
     re.compile(r"current to bundle v\d+(?:\.\d+)*[a-z]* / engine Mamey \d+(?:\.\d+)*[a-z]*"),
     f"current to bundle v{BUNDLE} / engine Mamey {ENGINE}"),
    ("docs/GUIDE/01_User_Manual.md",
     re.compile(r"the full suite at v\d+(?:\.\d+)*[a-z]* \(engine \d+(?:\.\d+)*[a-z]*\)"),
     f"the full suite at v{BUNDLE} (engine {ENGINE})"),
    ("docs/GUIDE/01_User_Manual.md",
     re.compile(r"should report `engine \d+(?:\.\d+)*[a-z]*, bundle \d+(?:\.\d+)*[a-z]*`"),
     f"should report `engine {ENGINE}, bundle {BUNDLE}`"),
    ("docs/standalone/CHATGPT_BATCH_PROTOCOL.md",
     re.compile(r"# Mamey v\d+(?:\.\d+)*[a-z]* ChatGPT Batch Protocol"),
     f"# Mamey v{ENGINE} ChatGPT Batch Protocol"),
    ("docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md",
     re.compile(r"(\*\*Version:\*\* [\d.]+ \u00b7 Mamey v)\d+(?:\.\d+)*[a-z]*( / Sapote v)\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>{ENGINE}\g<2>{BUNDLE}"),
    ("docs/GLOSSARY.md",
     re.compile(r"(Maintenance note:[^\n]*?engine )\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>{ENGINE}"),
    ("docs/GUIDE/03_Technical_Manual_Encyclopedia.html",
     re.compile(r"current to bundle v\d+(?:\.\d+)*[a-z]* / engine Mamey \d+(?:\.\d+)*[a-z]*"),
     f"current to bundle v{BUNDLE} / engine Mamey {ENGINE}"),
    # AUDIT v9.7.100 (docs-currency): 06_Concepts_QandA.md carries a header "Current to bundle vX / engine
    # Mamey Y" probe and a footer "current to bundle vX / engine Mamey Y" stamp. Neither was covered by
    # sync_version, so the Q&A footer silently drifted (footer said v9.7.99 while the header said v9.7.100).
    # Capture-group preserves the leading word's case so the capitalized header and lowercase mid-sentence
    # footer are both updated without mangling grammar.
    ("docs/GUIDE/06_Concepts_QandA.md",
     re.compile(r"([Cc]urrent to bundle v)\d+(?:\.\d+)*[a-z]*( / engine Mamey )\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>{BUNDLE}\g<2>{ENGINE}"),
    # AUDIT v9.7.99 (docs-currency): Encyclopedia <title> + nav "Encyclopedia · vX" were not covered
    # by any rule and drifted (v9.7.96 while bundle was v9.7.97/98). Now synced.
    ("docs/GUIDE/03_Technical_Manual_Encyclopedia.html",
     re.compile(r"Encyclopedia \u00b7 v\d+(?:\.\d+)*[a-z]*"),
     f"Encyclopedia \u00b7 v{BUNDLE}"),
    # PREREQUISITES.md self-ID in its H1 title (was stale at v9.7.2).
    ("PREREQUISITES.md",
     re.compile(r"# PREREQUISITES — Sapote–Mamey v\d+(?:\.\d+)*[a-z]*"),
     f"# PREREQUISITES — Sapote–Mamey v{BUNDLE}"),
    # v9.7.155 (anchor-the-rotting-fields): TIER_MANIFEST.txt header restates the bundle version
    # in its `version=` token. It is fully regenerated by make_public_tier.sh at cut time, but the
    # checked-in copy drifted (stale at 9.7.151 across v9.7.152-154) because no tool owned this token
    # between cuts. Anchor ONLY the version= value; tier= and stamp= are left to the cut to set.
    ("TIER_MANIFEST.txt",
     re.compile(r"(# TIER_MANIFEST tier=\S+ version=)\d+(?:\.\d+)*[a-z]*"),
     rf"\g<1>{BUNDLE}"),
    # INT-2 (v9.7.320): the `stamp=` token was explicitly "left to the cut to set" and owned by
    # nothing between cuts — the exact gap that shipped v97319b with a stale v97319a stamp
    # (TAG build= updated, TIER_MANIFEST stamp= not) while verify_release_identity read only
    # BUILD_STAMP. Anchor stamp= to the build STAMP so --apply keeps it current and --check flags drift.
    ("TIER_MANIFEST.txt",
     re.compile(r"(# TIER_MANIFEST tier=\S+ version=\d+(?:\.\d+)*[a-z]* stamp=)\S+"),
     rf"\g<1>{STAMP}"),
    # INT-2: the tier/user-guide docs restate the build stamp inline ("\u00b7 build <stamp>") as a freshness
    # probe, and none was under sync coverage — same rotting-field class. Anchor each so a cut can't
    # leave them stale. CODE-tier-shipped; skips where absent.
    ("TIER_SET_EXPLAINER.md",
     re.compile(r"\u00b7 build \w+"),
     f"\u00b7 build {STAMP}"),
    ("docs/user_guides/comprehensive_glossary.md",
     re.compile(r"\u00b7 build \w+"),
     f"\u00b7 build {STAMP}"),
    ("docs/user_guides/sapote_kernel_guide.md",
     re.compile(r"\u00b7 build \w+"),
     f"\u00b7 build {STAMP}"),
    # PROV-12: those same three docs also restate the bundle+engine literals in their header line
    # ("Bundle v\u2026 \u00b7 Engine \u2026" / "\u2026 \u00b7 engine Mamey \u2026"), which had drifted to
    # v9.7.319 / 1.9.111 while the build stamp above stayed current \u2014 only "\u00b7 build" was ever
    # anchored. Anchor the bundle and engine restatements too. Patterns are pinned to the header layout
    # so historical version mentions elsewhere in the same files (the glossary "v2/v3 additions \u2026
    # Bundle v9.7.319/9.7.246" footers, the kernel-guide "Engine 1.9.104 (v9.7.158)" changelog lines)
    # are never clobbered.
    ("TIER_SET_EXPLAINER.md",
     re.compile(r"Bundle v\d+(?:\.\d+)*[a-z]*"),
     f"Bundle v{BUNDLE}"),
    ("TIER_SET_EXPLAINER.md",
     re.compile(r"engine Mamey \d+(?:\.\d+)*[a-z]*"),
     f"engine Mamey {ENGINE}"),
    ("docs/user_guides/comprehensive_glossary.md",
     re.compile(r"Bundle v\d+(?:\.\d+)*[a-z]* \u00b7 Engine \d+(?:\.\d+)*[a-z]*"),
     f"Bundle v{BUNDLE} \u00b7 Engine {ENGINE}"),
    ("docs/user_guides/sapote_kernel_guide.md",
     re.compile(r"Sapote\u2013Mamey v\d+(?:\.\d+)*[a-z]* \u00b7 Engine \d+(?:\.\d+)*[a-z]*"),
     f"Sapote\u2013Mamey v{BUNDLE} \u00b7 Engine {ENGINE}"),
    # operational_reference embeds the stamp inside example tier-zip filenames (…-CODE-<stamp>.zip).
    ("docs/user_guides/operational_reference.md",
     re.compile(r"(sapote-mamey-v\d+(?:\.\d+)*[a-z]*-CODE-)\d+v\d+[a-z]*"),
     rf"\g<1>{STAMP}"),
    # v9.7.199 (F5, anchor-the-rotting-fields): TIER_NOTE_CODE.md restates bundle/engine/build in its H1
    # title + three body lines. Its own text says "regenerate at cut time," but nothing owned it, so it
    # drifted — stale v9.7.144b, then shipped v9.7.197 inside the v9.7.198 cut. The make_public_tier.sh
    # version-sync gate passed anyway because NO rule anchored this file. Anchor all four restatements so
    # --apply keeps them current and --check flags drift. CODE-tier-specific; skips where the file is absent.
    ("TIER_NOTE_CODE.md",
     re.compile(r"(?m)^# Sapote.Mamey v\d+(?:\.\d+)*[a-z]* CODE tier"),
     f"# Sapote\u2013Mamey v{BUNDLE} CODE tier"),
    ("TIER_NOTE_CODE.md",
     re.compile(r"(?m)^Build stamp: \S+"),
     f"Build stamp: {STAMP}"),
    ("TIER_NOTE_CODE.md",
     re.compile(r"(?m)^Engine: Mamey v\d+(?:\.\d+)*[a-z]*"),
     f"Engine: Mamey v{ENGINE}"),
    ("TIER_NOTE_CODE.md",
     re.compile(r"(?m)^Bundle: (?:sapote-mamey-)?v\d+(?:\.\d+)*[a-z]*"),
     f"Bundle: v{BUNDLE}"),
    # ROSTER_402 seed #2 (BC4): docs/EXTERNAL_TOOL_INVENTORY.md carried a stale 9.7.400
    # currency header through the .401 composition — caught BY HAND at seal; no rule owned
    # it and no test pinned it (the same rotting-field class as CURRENT_DOCS_INDEX's three
    # freezes). Its "**Bundle vX · engine Mamey Y · compiled DATE**" header (and the wiki
    # twin's) is a currency stamp, not history: anchor bundle+engine+compiled-date. Table
    # rows recording versions *actually run* (e.g. "Version (verified)") are provenance and
    # are deliberately NOT touched. Lock test: tests/test_docs_currency_stamp_lock_v97402.py.
    ("docs/EXTERNAL_TOOL_INVENTORY.md",
     re.compile(r"\*\*Bundle v\d+(?:\.\d+)*[a-z]* \u00b7 engine Mamey \d+(?:\.\d+)*[a-z]* \u00b7 compiled \d{4}-\d{2}-\d{2}\*\*"),
     f"**Bundle v{BUNDLE} \u00b7 engine Mamey {ENGINE} \u00b7 compiled {_STAMP_DATE}**"),
    ("wiki/External-Tools-and-Databases.md",
     re.compile(r"\*\*Bundle v\d+(?:\.\d+)*[a-z]* \u00b7 engine Mamey \d+(?:\.\d+)*[a-z]* \u00b7 compiled \d{4}-\d{2}-\d{2}\*\*"),
     f"**Bundle v{BUNDLE} \u00b7 engine Mamey {ENGINE} \u00b7 compiled {_STAMP_DATE}**"),
]


def plan_rule_updates(rules=None):
    """v9.7.405 (CODEX_390 third-gate hardening, hand-ported): validate EVERY anchored rule in
    memory before ANY version file is mutated.

    The prior write loop updated each matching file immediately and only reported a missing file
    or missing anchor after earlier files had already changed, so a typo in a late rule left a
    mixed-version tree even though the command exited non-zero. This planner applies the rules
    sequentially to an in-memory per-file image and returns (problems, complete write set); the
    caller writes nothing unless problems is empty.
    """
    rules = RULES if rules is None else rules
    originals, working, problems = {}, {}, []
    for rel, pat, repl in rules:
        p = ROOT / rel
        if not p.exists():
            problems.append(f"MISSING FILE: {rel}")
            continue
        if rel not in working:
            originals[rel] = p.read_text(encoding="utf-8")
            working[rel] = originals[rel]
        new, n = pat.subn(repl, working[rel])
        if n == 0:
            problems.append(f"PATTERN NOT FOUND in {rel}: {pat.pattern}")
        else:
            working[rel] = new
    updates = {rel: text for rel, text in working.items() if text != originals[rel]}
    return problems, updates


def changelog_headline() -> str:
    """v9.7.86 C1: derive the BUILD_STAMP `patch=` summary from the CHANGELOG top entry,
    so the stamp can never fall out of sync with the cut's actual content. Returns a
    one-line, semicolon-joined summary of the newest CHANGELOG entry's bolded headlines."""
    try:
        txt = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    # take the block from the first "# vX" header to the next "# vX" header
    lines = txt.splitlines()
    block, started = [], False
    for ln in lines:
        if ln.startswith("# v"):
            if started:
                break
            started = True
            continue
        if started:
            block.append(ln)
    # pull the bolded headline of each bullet (text between the first pair of **...**)
    heads = []
    for ln in block:
        m = re.search(r"-\s+\*\*(.+?)\*\*", ln)
        if m:
            heads.append(m.group(1).rstrip(":").strip())
    return "; ".join(heads[:8])


def sync_build_stamp_patch(check: bool) -> list[str]:
    """Rewrite (or --check) the BUILD_STAMP.txt `patch=` line from the CHANGELOG head."""
    p = ROOT / "BUILD_STAMP.txt"
    if not p.exists():
        return [f"MISSING FILE: BUILD_STAMP.txt"]
    txt = p.read_text(encoding="utf-8")
    head = changelog_headline()
    if not head:
        return ["could not derive patch line from CHANGELOG.md"]
    new = re.sub(r"(?m)^patch=.*$", f"patch={head}", txt)
    if new == txt:
        return []
    if check:
        return ["OUT OF SYNC: BUILD_STAMP.txt patch= line does not match CHANGELOG head"]
    atomic_write_text(p, new)
    return ["patched BUILD_STAMP.txt (patch= line)"]


def sync_bootstrap_contract(check: bool) -> tuple[bool, list[str]]:
    """v9.7.155: keep the generated bootstrap docs (BOOTSTRAP_FILE_AUDIT.md and the
    other render_bootstrap_contract.py surfaces) current as part of the single
    sync_version surface. The generator already derives its version/build from
    pyproject.toml + BUILD_STAMP.txt (the SSOT), so the only failure mode is
    forgetting to RUN it after a bump — which is exactly what left BOOTSTRAP_FILE_AUDIT.md
    stale at v9.7.153 in the v9.7.154 cut. In --check we invoke its --check; in write
    mode we invoke --apply. Delegated by subprocess so this stays the one command a
    cutter runs."""
    import subprocess
    tool = ROOT / "tools" / "render_bootstrap_contract.py"
    if not tool.exists():
        return True, []  # tool absent in some tiers; not an error here
    mode = "--check" if check else "--apply"
    try:
        out = subprocess.run(
            [sys.executable, str(tool), mode],
            cwd=str(ROOT), capture_output=True, text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, [f"bootstrap-contract sync timed out after 120 seconds ({mode})"]
    except Exception as e:
        return False, [f"bootstrap-contract sync could not run: {e}"]
    if check:
        if out.returncode != 0:
            # v9.7.410 hostile audit: the renderer refusing to RUN (no PyYAML under the system
            # python3, for one) was reported as "docs are stale" — a false OUT OF SYNC that sends
            # the cutter to re-render docs that are not stale. Still a failure (nothing was
            # verified), but say what actually happened.
            blob = (out.stderr or "") + (out.stdout or "")
            if "is required" in blob or "No module named" in blob or "Traceback" in blob:
                first = next((ln for ln in blob.splitlines() if ln.strip()), "renderer failed")
                return False, [f"CANNOT VERIFY bootstrap docs: render_bootstrap_contract.py could not "
                               f"run under {sys.executable} — {first.strip()[:160]}"]
            return False, ["OUT OF SYNC: generated bootstrap docs are stale "
                           "(run: python3 tools/render_bootstrap_contract.py --apply)"]
        return True, []
    # write mode: surface what changed (best-effort; tool prints its own line)
    if out.returncode == 0:
        return True, ["synced bootstrap docs (render_bootstrap_contract.py --apply)"]
    return False, [f"bootstrap-contract --apply failed: {out.stdout}{out.stderr}"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Synchronize Sapote-Mamey release identity restatements from pyproject.toml.")
    parser.add_argument("--check", action="store_true", help="fail if restated files are out of sync; do not write")
    ns = parser.parse_args(argv)
    check = ns.check
    problems, updates = plan_rule_updates()
    changed = []
    if check:
        problems.extend(f"OUT OF SYNC: {rel}" for rel in updates)
    elif problems:
        # v9.7.405: ALL-OR-NOTHING — one invalid rule means no version file is touched.
        sys.stderr.write("version sync REFUSED (no file written):\n"
                         + "\n".join("  " + x for x in problems) + "\n")
        sys.exit(1)
    else:
        # v9.7.405: the bootstrap-doc regeneration runs BEFORE any anchored write. It derives
        # from the SSOT (pyproject), so ordering is safe — and a failed or timed-out generator
        # refuses the whole bump instead of leaving anchors rewritten around stale docs.
        _bc_ok, _bc_msgs = sync_bootstrap_contract(check=False)
        if not _bc_ok:
            sys.stderr.write("version sync REFUSED (no file written):\n"
                             + "\n".join("  " + x for x in _bc_msgs) + "\n")
            sys.exit(1)
        for rel, text in updates.items():
            atomic_write_text(ROOT / rel, text)
            changed.append(rel)
        changed += _bc_msgs

    if check:
        if problems:
            sys.stdout.write(("version sync FAILED:") + "\n")
            sys.stdout.write(("\n".join("  " + x for x in problems)) + "\n")
            sys.exit(1)
        # C1: also check the BUILD_STAMP patch line
        bs = sync_build_stamp_patch(check=True)
        if bs:
            sys.stdout.write(("version sync FAILED:") + "\n")
            sys.stdout.write(("\n".join("  " + x for x in bs)) + "\n")
            sys.exit(1)
        # v9.7.155: also check the generated bootstrap docs are current
        _bc_ok, bc = sync_bootstrap_contract(check=True)
        if bc or not _bc_ok:
            sys.stdout.write(("version sync FAILED:") + "\n")
            sys.stdout.write(("\n".join("  " + x for x in bc)) + "\n")
            sys.exit(1)
        # v9.7.155 (Speed-Round Finding A): the BUILD_STAMP `build=` token encodes the
        # bundle version with dots stripped (e.g. 20260630v97155a -> 97155 == 9.7.155).
        # A bump that updates `version=` but forgets `build=` otherwise passes silently
        # AND gets baked into the bootstrap doc by the --apply wiring above. Guard it.
        # Round-2 Finding E: anchor the match (v<compact> then a letter-suffix or end) so
        # a shorter version (9.7.15 -> "9715") doesn't substring-match a longer build
        # (v97155a) and false-pass.
        bstamp = ROOT / "BUILD_STAMP.txt"
        if bstamp.exists():
            bs_txt = bstamp.read_text(encoding="utf-8")
            bm = re.search(r"(?m)^build=(\S+)", bs_txt)
            compact = BUNDLE.replace(".", "")
            if bm and not re.search(rf"v{re.escape(compact)}[a-z]?$", bm.group(1)):
                sys.stdout.write(("version sync FAILED:") + "\n")
                sys.stdout.write((f"  BUILD_STAMP build= ({bm.group(1)}) does not encode bundle "
                      f"{BUNDLE} (expected to contain 'v{compact}') — update build= for this cut.") + "\n")
                sys.exit(1)
        # C2: engine lineage check — ENGINE must have an entry in ENGINE_LINEAGE.md
        el_path = ROOT / "docs" / "ENGINE_LINEAGE.md"
        if el_path.exists():
            el_txt = el_path.read_text(encoding="utf-8")
            # Round-2 Finding F: anchor so engine X.Y.Z is not satisfied by a longer
            # entry (e.g. 1.9.10 must not match "Engine 1.9.101"). Require the version
            # to be followed by a non-digit boundary. (Cannot fire under monotonic
            # versioning today, but the substring class is closed here regardless.)
            if not re.search(rf"Engine {re.escape(ENGINE)}(?:\D|$)", el_txt):
                sys.stdout.write((f"version sync FAILED:") + "\n")
                sys.stdout.write((f"  ENGINE LINEAGE MISSING: engine {ENGINE} has no entry in docs/ENGINE_LINEAGE.md") + "\n")
                sys.stdout.write((f"  Add an entry before cutting a release (see PATCH-ENGINE-LINEAGE).") + "\n")
                sys.exit(1)
        else:
            sys.stdout.write((f"WARNING: docs/ENGINE_LINEAGE.md not found — engine lineage ungoverned") + "\n")
        sys.stdout.write((f"version sync OK  (engine {ENGINE}, bundle {BUNDLE})") + "\n")
        return

    # C1: sync the BUILD_STAMP patch line from the CHANGELOG head
    changed += sync_build_stamp_patch(check=False)

    # v9.7.155: regenerate the bootstrap docs from the SSOT so they never go stale on a bump
    # (bootstrap docs regenerated above, before the anchored writes — v9.7.405)

    for c in changed:
        sys.stdout.write((f"patched {c}") + "\n")
    if not changed:
        sys.stdout.write(("nothing to patch — already in sync") + "\n")
    if problems:
        sys.stdout.write(("\n".join(problems)) + "\n")
        sys.exit(1)
    sys.stdout.write((f"done — engine {ENGINE}, bundle {BUNDLE}") + "\n")


if __name__ == "__main__":
    main()
