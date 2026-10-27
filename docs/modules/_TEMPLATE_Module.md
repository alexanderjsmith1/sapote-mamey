# Sapote-Mamey Module Template — for adding a new Deliverable or Knowledge module

**Filing.** `docs/modules/_TEMPLATE_Module.md`. Copy this file, rename to `DELIVERABLE_<Name>.md` or
`KNOWLEDGE_<Name>.md`, and fill every `<…>`. Delete the sections that don't apply (a KNOWLEDGE module usually
drops §3 Pipeline and §5 Acceptance; a DELIVERABLE module keeps all of them).

A module page should let a reader produce the output from the package alone. Point to existing rules instead of
restating them, and say which document wins in a conflict.

---

## 0. Header block (every module has this)
> **Filing.** `<path within docs/>`.
> **Extends / references:** `<DELIVERABLE_CONTRACT.md / FIGURE_STYLE.md / DAPR_CLASS_FRAMEWORK.md / …>` — name
> the docs whose rules this module inherits, and **do not restate those rules**, only point to them.
> **Precedence.** `DELIVERABLE_CONTRACT.md` wins over a module; the current user request and authorization govern actions; inherited documents define the selected workflow, and actual source governs implementation.
> **Status:** `<CODE_BACKED | PROMPT_BACKED | SCHEMA_BACKED>` (which layer produces the artifact).
> **One-line purpose.** `<what a user gets, in one sentence>`.

---

## 1. When it is offered (Deliverable Offer Protocol)
`<Name the user-selected workflow and trigger that makes this artifact applicable.
State its completion evidence and what remains incomplete within that scope. A
trigger may support a useful offer; it does not itself authorize a new analysis,
network submission, package mutation, all-BGC authoring or publication. Distinguish
a documented recommendation from an implemented automatic invocation.>`
*(KNOWLEDGE modules: replace with "Why this exists / who reads it".)*

---

## 2. Inputs required
| File / field | Feeds | Required for |
|---|---|---|
| `<input>` | `<which output>` | `<which sub-deliverable>` |

State the **skip-not-fake** rule: a sub-output whose inputs are absent is omitted and labeled, never fabricated.

---

## 3. Pipeline (exact, ordered commands)  *(DELIVERABLE only)*
```bash
python tools/<tool>.py --banked-dir <dir> --out-dir <dir> <flags>
…
```
List only flags implemented by that exact tool and verified against its parser;
the placeholders above do not establish a common flag interface. Name the owning
function for computed values, admitted inputs, output/write boundaries and receipts.

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
- [ ] Complete locus identity on each operational BGC reference: strain, full contig/node, region and alias.
- [ ] Hand back the result, its evidence and open holds.

---

## 6. Tool / knowledge inventory
`<Which files own which pieces, one row each, so a runner can find the source of truth fast.>`

---

## 7. Next-paths closer
`<Hand back the result, its evidence and open holds. Add a next step only when one is useful.>`

---

### Authoring notes (delete before filing)
- Keep it **paste-ready**: a reader with only this file and the package should get the output right.
- **Reference, don't restate** — restating a rule is how two copies drift. Point to the canonical doc.
- **State precedence** explicitly so a runner knows what wins in a conflict.
- Put every computed number behind "the code is the source of truth"; modules carry the *portable copy*, not the
  authority.
- A DELIVERABLE module without an Offer Protocol (§1) and an Acceptance checklist (§5) is incomplete.
