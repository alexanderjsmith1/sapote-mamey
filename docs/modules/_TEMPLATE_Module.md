# Sapote-Mamey Module Template — for adding a new Deliverable or Knowledge module

**Filing.** `docs/modules/_TEMPLATE_Module.md`. Copy this file, rename to `DELIVERABLE_<Name>.md` or
`KNOWLEDGE_<Name>.md`, and fill every `<…>`. Delete the sections that don't apply (a KNOWLEDGE module usually
drops §3 Pipeline and §5 Acceptance; a DELIVERABLE module keeps all of them).

The goal: a new module should be **pasteable into a fresh Sapote/Mamey chat** and have the workflow behave
correctly with no other context. Two locks make that possible — **reference, don't restate** existing rules, and
**state precedence** so a fresh runner knows what wins.

---

## 0. Header block (every module has this)
> **Filing.** `<path within docs/>`.
> **Extends / references:** `<DELIVERABLE_CONTRACT.md / FIGURE_STYLE.md / DAPR_CLASS_FRAMEWORK.md / …>` — name
> the docs whose rules this module inherits, and **do not restate those rules**, only point to them.
> **Precedence.** `DELIVERABLE_CONTRACT.md` wins over a module; the active parent monolith wins over everything.
> **Status:** `<CODE_BACKED | PROMPT_BACKED | SCHEMA_BACKED>` (which layer produces the artifact).
> **One-line purpose.** `<what a user gets, in one sentence>`.

---

## 1. When it is offered (Deliverable Offer Protocol)
`<The trigger state — what condition or user phrasing makes this deliverable due. State the "incomplete delivery"
condition: what it means to have stopped short. Per DELIVERABLE_CONTRACT, the user must never need to know the
deliverable exists to receive it: auto-build it, or offer it as the first next-path.>`
*(KNOWLEDGE modules: replace with "Why this exists / who reads it".)*

---

## 2. Inputs required
| File / field | Feeds | Required for |
|---|---|---|
| `<input>` | `<which output>` | `<which sub-deliverable>` |

State the **skip-not-fake** rule: a sub-output whose inputs are absent is omitted and labelled, never fabricated.

---

## 3. Pipeline (exact, ordered commands)  *(DELIVERABLE only)*
```bash
python tools/<tool>.py --banked-dir <dir> --out-dir <dir> <flags>
…
```
Note the shared reproducibility flags the tool honors (`--replot`, `--dpi`, `--no-register`, etc.) and the single
source of truth for any computed value (which function in which tool).

---

## 4. Outputs & the manifest / contract surface
`<List every artifact produced and its stable id. If it registers into a manifest or schema, give the schema and
state that registration — not hand-editing — is the single source of truth.>`

---

## 5. Acceptance checklist ("done" means all of these)  *(DELIVERABLE only)*
- [ ] Inherited rules satisfied (name them: FIGURE_STYLE / FIGURE_REPRODUCIBILITY / schema validator / …).
- [ ] Public/private boundary respected if any unpublished (AS) data could be involved — with an explicit leak
      audit for any public artifact.
- [ ] Canonical numbers match the knowledge modules; no retired figures.
- [ ] Contig-ID locator on every BGC reference (§4 Contig-ID Mandate).
- [ ] No retired internal/personal codenames; affiliation = .
- [ ] Closes with **exactly 8 unique plain-text numbered next-paths**, never widgets (Next-Paths Protocol).

---

## 6. Tool / knowledge inventory
`<Which files own which pieces, one row each, so a runner can find the source of truth fast.>`

---

## 7. Next-paths closer
`<A worked example of the exactly-8-path closer for this deliverable, so even a first-time runner ends correctly.>`

---

### Authoring notes (delete before filing)
- Keep it **paste-ready**: a fresh chat with only this file should behave correctly.
- **Reference, don't restate** — restating a rule is how two copies drift. Point to the canonical doc.
- **State precedence** explicitly so a runner knows what wins in a conflict.
- Put every computed number behind "the code is the source of truth"; modules carry the *portable copy*, not the
  authority.
- A DELIVERABLE module without an Offer Protocol (§1) and an Acceptance checklist (§5) is incomplete.
