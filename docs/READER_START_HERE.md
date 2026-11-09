# Start with your file

Pick the row that matches what you have. Each guide gets you to a useful result
without installing every optional tool. Terms are in the [glossary](GLOSSARY.md).

| What do you have? | Go to |
|---|---|
| An **antiSMASH result ZIP** (antiSMASH's output for one genome) | [Your first run](reader/01_FIRST_RUN.md). It builds a package, the workbook and the issue log. |
| A **`Complete_Package.zip`** (the saved result an earlier Mamey run wrote) | [Read one saved package](reader/03_READ_RESULTS.md). Extract it and open `OPEN_ME_FIRST.html`. |
| A **genome FASTA** (the raw sequence) | Run antiSMASH on it first, at https://antismash.secondarymetabolites.org or with a local install. The [antiSMASH web submission guide](ANTISMASH_WEB_SUBMISSION_SOP.md) gives the settings. Download the result ZIP; Mamey reads that, not the FASTA. Then go to [Your first run](reader/01_FIRST_RUN.md). |
| **Nothing yet** | Practice on a public genome: [public antiSMASH datasets](PUBLIC_DATASETS.md). Then set up with [Inputs and setup](reader/02_INPUTS_AND_SETUP.md). |

Other starting points:

- The program itself arrived as a code ZIP: [Inputs and setup](reader/02_INPUTS_AND_SETUP.md).
- A run failed: [Recovery and limits](reader/04_RECOVERY_AND_LIMITS.md).
- You want a figure, a card or a comparison: [Choose a task](USER_TASK_ROUTER.md).
- You want an assistant to do the steps: [Your first analysis](MASTER_WALKTHROUGH.md), route A.

Keep your original antiSMASH ZIP unchanged. Every later step reads it.
