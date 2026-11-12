# Start with your file

Pick the row that matches what you have. Each guide gets you to a useful result
without installing every optional tool. Terms are in the [glossary](GLOSSARY.md).

| What do you have? | Go to |
|---|---|
| An **antiSMASH result ZIP** (antiSMASH's output for one genome) | [Your first run](reader/01_FIRST_RUN.md). It builds a package, the workbook and the issue log. |
| A **`Complete_Package.zip`** (the saved result an earlier Mamey run wrote) | [Read one saved package](reader/03_READ_RESULTS.md). Extract it, then open `OPEN_ME_FIRST.html`, or `issue_log.md` if the page is missing. |
| A **genome FASTA** (the raw sequence) | Run antiSMASH on it first, at https://antismash.secondarymetabolites.org or with a local install. The public server receives the sequences you upload, so check that you may share them. The [antiSMASH web submission guide](ANTISMASH_WEB_SUBMISSION_SOP.md) gives the settings. Download the result ZIP, then go to [Your first run](reader/01_FIRST_RUN.md). |
| **Nothing yet** | Practice on a public genome: [public antiSMASH datasets](PUBLIC_DATASETS.md). Then set up with [Inputs and setup](reader/02_INPUTS_AND_SETUP.md). |

Other starting points:

- The program itself arrived as a code ZIP: [Inputs and setup](reader/02_INPUTS_AND_SETUP.md).
- Someone sent you a package to review: [Read one saved package](reader/03_READ_RESULTS.md).
  To check it again, validate a copy, because `validate` updates `package_status.json`.
- You have a folder of antiSMASH ZIPs: [the batch guide](INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md).
  Do one ZIP with [Your first run](reader/01_FIRST_RUN.md) first.
- You have a validated package and want cards or figures: [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md)
  or [figures](FIGURES_START_HERE.md). Some of these commands write into the package, so
  read [post-seal readers](POSTSEAL_READERS.md) and work on a copy.
- A run failed: [Recovery and limits](reader/04_RECOVERY_AND_LIMITS.md).
- You want another task, such as a comparison: [Choose a task](USER_TASK_ROUTER.md).
- You want an assistant to do the steps: [Ask an assistant to run it](MASTER_WALKTHROUGH.md).

Keep your original antiSMASH ZIP unchanged. A new run, a sequence-level check and a
portable ZIP with region files need it. Reading a saved package does not.
