# antiSMASH web submission: standard operating procedure

This page covers how reference genomes reach the public antiSMASH server (`https://antismash.secondarymetabolites.org`) for a Sapote-Mamey project. It is a procedure, not a tool. The bundle ships no code that submits to the public server, and every batch needs the project owner's named authorisation.

The server is a shared public resource. The rules below keep this project's use light: it never adds to a queue other people are waiting in.

## 1. Who decides what
- **The project owner authorises each batch by name,** for example "the nearest type strains" or "the five FASTA resubmissions". One authorisation covers one named set and does not roll forward.
- **The owner sets pacing and strictness.** A number on the server page is evidence to bring to the owner, not a licence to change pacing.
- **A resubmission is a new submission.** It needs a written reason and its own authorisation, including a resubmission by a different route.

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
- **Never pool strictnesses.** Loose and relaxed are separate passes, each with its own authorisation.

## 3. Input routes
| Route | When | How |
|---|---|---|
| A. Get from NCBI (default) | an INSD record with CDS annotation: a complete chromosome (`CP…`, `AP…`) or a WGS master whose contigs are annotated | `ncbi=<accession>` |
| B. FASTA upload with Prodigal | the deposit has no CDS (`all records skipped`), or the genome is held only as FASTA | `seq=@<file>.fna`, `genefinder=prodigal`; needs its own authorisation |

**Never use route A for these:**
- RefSeq (`NZ_…`) or assembly (`GCF_`/`GCA_`) accessions; they fail with `Failed to download file from NCBI`. Use the INSD primary.
- WGS masters with unannotated contigs; they fail with `all records skipped`.

A route B job uses Prodigal's gene calls, not NCBI's; say so in the job record.

## 4. Before submitting (preflight)
1. **Bind the batch** in one queue table: accession, organism, size in Mb, why it is wanted, and the isolate it serves.
2. **Subtract what is held,** matching on accession or WGS prefix, never on strain name. Check for finished jobs never downloaded (section 7) before resubmitting anything.
3. **Check for annotation** (route A) with NCBI `datasets summary genome accession <GCA>`.
   - A GenBank (GCA) record without `annotation_info` needs route B.
   - A RefSeq (GCF) record with PGAP annotation does not count, because route A fetches the INSD record.
4. **Flag genomes outside 5–12 Mb** in the queue table; do not drop the row.
5. **Map WGS contig ids to their master** (`ABCD01000009` → `ABCD00000000.1`), and de-duplicate on the four-to-six-letter prefix.

## 5. Submitting
1. **Light-touch rule: no submission if there is a queue.** Before each submission, read `GET /api/v1.0/stats` and submit only if both hold:
   - `queue_length` is 0;
   - `running` is below 60. A real queue forms once about 65 jobs run at once, and the cap leaves a margin under that.

   If either fails, pause, do not finish "just this batch", and tell the project owner. Recheck no sooner than 10 minutes later.
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
- Check status when a wave should have drained, or when the owner asks. Do not poll the status API in a loop.
- **Download every finished job.** Before closing a batch, compare the job list with the downloaded ZIPs and the server states.

## 8. Intake: a downloaded ZIP is not yet filed
1. The ZIP opens and holds region `.gbk` files.
2. **Read the organism from the ZIP's own GenBank** (`ORGANISM` or `DEFINITION`), never from the file name or the batch. A FASTA upload carries no organism: take the genus from the queue table, and say so.
3. **Read the strictness from the ZIP's JSON,** not from what was requested.
4. **Check drafts:** compare the record count with the contig count (contigs under 1 kb drop out), and check the 5–12 Mb band.
5. **Keep the ZIPs.** BiG-SCAPE and other downstream steps read their region GenBank files.

## 9. Failures: classify, record, don't retry
| Symptom | Cause | Disposition |
|---|---|---|
| `Failed to download file from NCBI` | a RefSeq or assembly accession was given | resubmit with the INSD primary, with authorisation |
| `all records skipped`, the record is a WGS master stub | no sequence | no route; drop it |
| `all records skipped`, the record has 0 CDS | an unannotated deposit | route B, with its own authorisation |
| a Python traceback inside antiSMASH | a service-side bug on that record | record it; a retry fails the same way |
| own job `queued` 20–30 s, with `queue_length` 0 and `running` under 60 | a transient early-stage bottleneck | none; it starts by itself |
| own job `queued` for more than 2 minutes | submissions too close together, or a real queue | wait; do not resubmit; check the stats and tell the owner |

Record every failure with its set, accession, organism, job, cause (not just the message) and disposition. Two symptoms above give the same message from opposite causes.

## 10. Never
- Never submit without a batch authorised by name.
- Never put an email address or any personal identifier in a request.
- Never submit while `queue_length` is above 0 or `running` is 60 or more.
- Never have more than 5 of your jobs queued or running at once.
- Never submit closer together than 45 seconds.
- Never retry automatically.
- Never pool loose and relaxed results, or runs with different feature sets.
- Never name or file a result from its file name; read its own GenBank.
- Never close a batch with finished jobs left on the server.
