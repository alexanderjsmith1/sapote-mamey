# Work with an assistant

An AI coding assistant can run the bundle for you, read a finished package, or draft
text from selected results. This page says what to give it, what to ask, and what to
check in its answer. It applies to any assistant that can read files and run commands.

To run the first analysis yourself, follow [Your first run](reader/01_FIRST_RUN.md). To
have an assistant do it, use [Route A in the first walkthrough](MASTER_WALKTHROUGH.md).
For other work, pick a route in [Choose a task](USER_TASK_ROUTER.md). An assistant can
read the same routes from [the task-routing JSON](USER_TASK_ROUTER.json).
Terms such as BGC, KCB and Mode B are defined in the [glossary](GLOSSARY.md).

## What to give it

Give the assistant four things.

1. The program folder, the one that holds `mamey_run.py`.
2. The input: an antiSMASH result ZIP, or a finished package folder.
3. The question, in one or two sentences.
4. A folder to save into. Say that the original ZIP must stay unchanged.

Tell it to read `AGENTS.md` first. That file is the operating contract for every
assistant, and some tools do not load it on their own.

Three kinds of file get mixed up, so name which you mean:

- The **code bundle** is the program.
- An **antiSMASH result ZIP** holds antiSMASH's annotations. Mamey reads it; it does not run antiSMASH.
- A **package** is the folder Mamey writes from one ZIP: tables, a workbook and an issue log.

Copy taxonomy and isolation source from a real record. Leave unknown values unknown.

## What to ask

Ask for a result you can check, not for "an analysis". Two examples:

> Read AGENTS.md. Inspect my EXAMPLE antiSMASH ZIP, run extraction and validate the
> package with `--workbook-strict`. Keep the original ZIP unchanged. Stop before any online search. Tell me the
> exit code, the `Package:` path, and any `[BLOCKING]` line in `issue_log.md`.

> Read runs/EXAMPLE/package and explain the main observations in two to four
> sentences. Link each claim to its source row. Keep observations and interpretations
> apart. List the missing evidence that could change the answer. Save the draft in
> reviews/EXAMPLE/.

For a document-only task, say so: "Read the guide and propose changes. Do not install or
run the software." [Assistant governance](ASSISTANT_GOVERNANCE.md) sets the permission
boundaries. If your assistant has a short session limit, see
[runtime profiles](ASSISTANT_RUNTIME_PROFILES.md). Capped mode (`--capped-session`)
turns off the written brief and the main antiSMASH JSON walker, and turns automatic gene
maps off unless you asked for them. KnownClusterBlast text is still read, and a separate record
pass still reads TIGRFAM hits. Agree to it before the assistant uses it.

## What to check in the answer

A run is done only when the assistant shows evidence. Ask for these and look at them yourself:

- The exit code of `run`. `0` is finished. `1` means not finished or a `[BLOCKING]` issue. `2` means the command was refused before any work. [Your first run](reader/01_FIRST_RUN.md#4-check-that-the-run-worked) explains each.
- The real paths of the workbook, the issue log and `OPEN_ME_FIRST.html`. Open them. [Read one saved package](reader/03_READ_RESULTS.md) explains the status words.
- Any channel that failed or did not run. A missing result is not a negative result.
- For a failed run, the last error and the kept output folder. [Recovery and limits](reader/04_RECOVERY_AND_LIMITS.md) covers the next step.

For one locus, the answer must name it as **strain / full node-or-contig / region / BGC alias**,
copied from the source record. A bare alias is not enough.

Keep three claims apart: sequence similarity, predicted chemistry, and measured activity.
A similar known cluster does not show the strain makes that compound. A Mode B card
needs its own steps: emit the template, write it, then verify it. See
[the Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md). A template alone is not a finished
card. Activity predictions from another program are optional and are never Mamey's own scores; the
[external activity contract](AB_AF_EXTERNAL_ACTIVITY_CHANNEL.md) is a developer page.

## Ask for a report

Ask for a short evidence brief, a table of claims and sources, and questions for you to
review. Each claim row should have:

- the full locus name;
- the source record and its checksum;
- whether the claim is an observation or an inference;
- what is still uncertain.

After your review, record which wording was accepted, revised or withheld. If an
assistant helped write the draft, keep its prompt, model name if known, the sources it
used, and your edits. When a source changes, check the claims that depend on it again.
Save the reviewed file separately from the template. [Evidence to report](EVIDENCE_TO_REPORT.md)
covers figures, captions and Methods facts.

## Optional work

Before an online search, agree which proteins go to which service. Use saved results when
they answer the question. Before a large comparison or tree run, agree the inputs, tools,
thread count, disk budget and expected run time. Agree again if any of them change.

For figures, use [Make and review figures](FIGURES_START_HERE.md). For a strain deck,
use [Strain slides](STRAIN_SLIDES.md).

## Next paths, automatic save state and transcripts

At the end of a substantial task, a good assistant gives numbered next steps, with a
recommendation, and saves a checkpoint. The rules it follows are in
[AGENTS.md](../AGENTS.md#next-paths-automatic-save-state-and-transcripts).

Ask for one checkpoint file that lists:

- the goal and agreed scope;
- the input checksums;
- the commands run and the output paths;
- checks done, errors, and the next action.

Check that the file exists and opens. A transcript is a separate record of the
conversation. A checkpoint is a summary and is not a transcript.

To resume, give the next assistant the checkpoint. Keep failed outputs and logs. Write
a retry to a new output folder. Before updating a master workbook, keep a copy and
confirm which run it came from.
