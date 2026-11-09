# antiSMASH web submission: standard operating procedure

> Project policy for the public antiSMASH server. The settings in section 2 and the pacing numbers in sections 5 and 10 are this project's own choices, not server rules. Service settings and limits change; check the server's current documentation before each batch, and record each job's accession, settings, URL and archive hash. For one genome in the browser, use the section 2 settings, leave email blank, and download the ZIP. When the diagnostics do not support a cause for an error, record `CAUSE_UNRESOLVED`.

## Local intake limitations

The local reader recovers strictness and identity evidence; it does not certify a live job's settings or all-region consistency. Mamey reads the organism from the first region GenBank header and rejects `ORGANISM .`. It can fall back to the filename, with a warning. Review the resolved identity before filing: a filename-derived label is not verified organism provenance. See [input troubleshooting](troubleshooting/ANTISMASH_INPUT_WORKFLOW.md) and [the antiSMASH profile page](ANTISMASH_PROFILE.md). A downloaded ZIP, a normal command exit and a sealed package are separate states.

This page covers how reference genomes reach the public antiSMASH server (`https://antismash.secondarymetabolites.org`) for a Sapote-Mamey project. It is a procedure, not a tool. The bundle ships no code that submits to the public server, and every batch needs the named authorization of the person who runs the project (the project lead).

The server is a shared public resource. The rules below keep this project's use light: it never adds to a queue other people are waiting in.

## 1. Who decides what
This section is for shared projects. If you run the project alone, you are the project lead: name your batch in your job record before you submit it.

- **The project lead authorizes each batch by name,** for example "the nearest type strains" or "the five FASTA resubmissions". One authorization covers one named set and does not roll forward.
- **The project lead sets pacing and strictness.** A number on the server page is evidence to bring to the lead, not a license to change pacing.
- **A resubmission is a new submission.** It needs a written reason and its own authorization, including a resubmission by a different route.

## 2. Settings: every job, every route
| Setting | Value | API field |
|---|---|---|
| Job type | the current web version (antiSMASH 8.0.x in 2026) | `jobtype=antismash8` |
| Detection strictness | loose | `hmmdetection_strictness=loose` |
| Extra features | all 11 on | `knownclusterblast`, `clusterblast`, `subclusterblast`, `cc_mibig`, `asf`, `rre`, `clusterhmmer`, `pfam2go`, `tigrfam`, `tfbs`, `ncbi_context` = `true` |
| Email | blank, always | no field sent |
| Gene finding | from the NCBI record; Prodigal only for FASTA uploads | `genefinder=prodigal` (FASTA route only) |

- **Why 11:** "All on" in the browser turns on 11 of 12 boxes; the twelfth needs an annotation file.
- **Five of the 11 are off by default** (ClusterBlast, Cluster Pfam, Pfam-GO, TIGRFam, NCBI context). A run without them is a different analysis; never pool it with these results.
- **Why no email:** no personal identifier goes on an outbound request. The job URL is therefore the only way back to a result.
- **Never pool strictnesses.** Loose and relaxed are separate passes, each with its own authorization.

## 3. Input routes
| Route | When | How |
|---|---|---|
| A. Get from NCBI (default) | an INSD record with CDS annotation: a complete chromosome (`CP…`, `AP…`) or a WGS master whose contigs are annotated | `ncbi=<accession>` |
| B. FASTA upload with Prodigal | the deposit has no CDS (`all records skipped`), or the genome is held only as FASTA | `seq=@<file>.fna`, `genefinder=prodigal`; needs its own authorization |

**Never use route A for these:**
- RefSeq (`NZ_…`) or assembly (`GCF_`/`GCA_`) accessions. In this project they have failed with `Failed to download file from NCBI`. Use the INSD primary.
- WGS masters with unannotated contigs; can produce `all records skipped`; inspect diagnostics before assigning the cause.

A route B job uses Prodigal's gene calls, not NCBI's; say so in the job record.

## 4. Before submitting (preflight)
1. **Bind the batch** in one queue table: accession, organism, size in Mb, why it is wanted, and the isolate it serves.
2. **Subtract what is held,** matching on the versioned accession or versioned WGS master, never on strain name or a bare prefix. Check for finished jobs never downloaded (section 7) before resubmitting anything.
3. **Check for annotation** (route A) with `datasets summary genome accession <GCA>`. This is the NCBI `datasets` command-line tool; install it from NCBI first. Read the `annotation_info` field in its output.
   - A GenBank (GCA) record without `annotation_info` needs route B.
   - A RefSeq (GCF) record with PGAP annotation does not count, because route A fetches the INSD record.
4. **Flag genomes outside 5–12 Mb** in the queue table; do not drop the row.
5. **Map WGS contig ids to their master** (`ABCD01000009` → `ABCD00000000.1`). The prefix stays the same across assembly versions, and the two digits after it give the version (`ABCD01…` vs `ABCD02…`). Treat rows that share a prefix as possible duplicates, not as the same genome: compare the versioned master and the assembly accession before you drop one.

## 5. Submitting
1. **Light-touch rule: no submission if there is a queue.** Before each submission, read `GET /api/v1.0/stats` and submit only if both hold:
   - `queue_length` is 0;
   - `running` is below 60. A real queue forms once about 65 jobs run at once, and the cap leaves a margin under that.

   If either fails, pause, do not finish "just this batch", and tell the project lead. Recheck no sooner than 10 minutes later.
2. **A brief "queued" on your own job is not a queue.** When few jobs are running (around 20), a new job can show `queued` for 20–30 seconds while it passes an early stage, then start. Do not count that as a queue, do not resubmit, and do not slow down beyond the normal spacing.

   It is a real queue only if `queue_length` is above 0, `running` is 60 or more, or your own job stays `queued` for more than 2 minutes.
3. **Keep at most 5 of your jobs on the server at once,** counting jobs that are queued or running. This is the limit the antiSMASH submission page asks users to keep to. Wait for a job to finish before submitting the sixth.
4. **Space submissions at least 45 seconds apart.** Jobs under 10 seconds apart have stuck as `queued`.
5. **Submit through the API:**
   ```bash
   curl -s -F "ncbi=<ACCESSION>" -F jobtype=antismash8 -F hmmdetection_strictness=loose \
     -F knownclusterblast=true -F subclusterblast=true -F clusterblast=true -F cc_mibig=true -F asf=true \
     -F rre=true -F clusterhmmer=true -F pfam2go=true -F tigrfam=true -F tfbs=true -F ncbi_context=true \
     https://antismash.secondarymetabolites.org/api/v1.0/submit
   ```
   For route B, replace `-F "ncbi=…"` with `-F "seq=@<file>.fna" -F genefinder=prodigal`.
6. **Record the job URL before the next submission,** with a comment line: set, order number, accession, organism, Mb, the isolate it serves, route and UTC time. The link lives about two weeks and there is no email fallback.
7. **Never retry automatically.** A failed submission is recorded, not repeated.

## 6. Read back what the server ran
Once per batch, read `GET /api/v1.0/status/<job>` for one job and confirm `loose` and all 11 features `True`.

## 7. Poll and download: once per wave, never in a loop
- Check status when a wave should have drained, or when the project lead asks. Do not poll the status API in a loop.
- **Download every finished job.** Before closing a batch, compare the job list with the downloaded ZIPs and the server states.

## 8. Intake: a downloaded ZIP is not yet filed
1. The ZIP opens and holds region `.gbk` files.
2. **Read the organism from the ZIP's own GenBank** (`ORGANISM` or `DEFINITION`), never from the file name or the batch. A FASTA upload carries no organism: take the genus from the queue table, and say so.
3. **Read the strictness from the ZIP's own antiSMASH JSON,** not from what was requested. `inspect` does not print it. After a `run`, read `antismash_profile_record` in the package `manifest.json` (also in `_1_intake.json`). It holds `requested`, `used`, `archive_recorded`, `archive_evidence` and `state`. `antismash_profile` alone is the value the run used, which may be what you typed rather than what the archive records. Pool by `antismash_profile_record.state` and `archive_recorded`: `MISMATCH_ARCHIVE_DIFFERS` or `ARCHIVE_UNREADABLE` means do not pool yet. `tools/check_antismash_profile.py` still reads only `antismash_profile` ([strictness](ANTISMASH_PROFILE.md)).
4. **Check drafts:** compare the record count with the contig count (contigs under 1 kb drop out), and check the 5–12 Mb band.
5. **Keep the ZIPs.** BiG-SCAPE and other downstream steps read their region GenBank files.

## 9. Failures: classify, record, don't retry
The second column is the likely cause seen before in this project. It is a hypothesis to check, not a diagnosis.

| Symptom | Likely cause to check | Check before acting | Disposition once checked |
|---|---|---|---|
| `Failed to download file from NCBI` | a RefSeq or assembly accession was given | the accession you submitted, read back from the job status | resubmit with the INSD primary, with authorization |
| `all records skipped`, the record is a WGS master stub | no sequence | the NCBI record itself | no route; drop it |
| `all records skipped`, the record has 0 CDS | an unannotated deposit | `annotation_info` (section 4, step 3) | route B, with its own authorization |
| a Python traceback inside antiSMASH | a service-side bug on that record | the full traceback | record it; one traceback does not show the bug recurs |
| own job `queued` 20–30 s, with `queue_length` 0 and `running` under 60 | a transient early-stage bottleneck | the stats and job status a minute later | none if it starts by itself |
| own job `queued` for more than 2 minutes | submissions too close together, or a real queue | the stats and your own submission times | wait; do not resubmit; tell the lead |

Record every failure with its set, accession, organism, job, the cause the checks support or `CAUSE_UNRESOLVED` (not just the message) and disposition. Two `all records skipped` rows above share a message but have different causes.

## 10. Never
- Never submit without a batch authorized by name.
- Never put an email address or any personal identifier in a request.
- Never submit while `queue_length` is above 0 or `running` is 60 or more.
- Never have more than 5 of your jobs queued or running at once.
- Never submit closer together than 45 seconds.
- Never retry automatically.
- Never pool loose and relaxed results, or runs with different feature sets.
- Never name or file a result from its file name; read its own GenBank.
- Never close a batch with finished jobs left on the server.
