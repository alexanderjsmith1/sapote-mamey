"""Fabricated software controls only; no native HMM or biological execution."""
import hashlib
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
import pytest
from unittest.mock import patch

HERE = Path(__file__).resolve()
SPEC = importlib.util.spec_from_file_location("owned_merge75", HERE.parents[1] / "tools/ripper_merge_e90.py")
merge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merge)


def database(hit_affinity="REAL", raw_rows=None, hit_rows=()):
    db = sqlite3.connect(":memory:")
    db.execute("create table ripper(acc text,species text,ppser integer,fastaid text,aaseq text,ppstrand integer,testrand integer,pptedist integer,score real)")
    db.execute("create table pfamscan(qname text,hname text,signif " + hit_affinity + ",hdesc text,collection text)")
    rows = raw_rows if raw_rows is not None else [("FABRICATED", "fabricated software fixture", 1, "FAKE_1", "MOCK", 1, 1, 12, 7.5)]
    db.executemany("insert into ripper values(?,?,?,?,?,?,?,?,?)", rows)
    db.executemany("insert into pfamscan values(?,?,?,?,?)", hit_rows)
    db.commit()
    return db


def coverage(db, noncomplete=None):
    ids = [row[0] for row in db.execute("select fastaid from ripper")]
    pairs = []
    for item in ids:
        for collection in sorted(merge.COLLECTIONS):
            present = db.execute("select count(*) from pfamscan where qname=? and collection=?", (item, collection)).fetchone()[0]
            pairs.append({"FastaID": item, "collection": collection,
                          "state": noncomplete or ("COMPLETE_HIT" if present else "COMPLETE_NO_HIT")})
    return {"schema": "ripper-annotation-coverage-proposal/1", "execution_provenance": "FABRICATED_SOFTWARE_CONTROL", "pairs": pairs}


class MergeSemantics(unittest.TestCase):
    def test_main_best_across_collections(self):
        db = database(hit_rows=[("FAKE_1", "pfam_fake", .01, "fake pfam", "pfam"), ("FAKE_1", "ripp_fake", .001, "fake ripp", "ripp")])
        files, receipt = merge.render(db, coverage(db))
        self.assertIn("ripp_fake", files["out.txt"])
        self.assertEqual(receipt["main_output_count"], 1)
        self.assertEqual(receipt["annotation_execution"], "NOT_OBSERVED_BY_MERGE_ADAPTER")

    def test_distant_requires_ripp_even_when_pfam_is_stronger(self):
        raw = [("FABRICATED", "fake", 9001, "FAKE_9001", "MOCK", -1, 1, 22, 4)]
        db = database(raw_rows=raw, hit_rows=[("FAKE_9001", "pfam_fake", 1e-12, "fake", "pfam"), ("FAKE_9001", "ripp_fake", .02, "fake", "ripp")])
        files, receipt = merge.render(db, coverage(db))
        self.assertIn("ripp_fake", files["distant.txt"])
        self.assertNotIn("pfam_fake", files["distant.txt"])
        self.assertIn("\tno\t", files["distant.txt"])
        self.assertEqual(receipt["distant_output_count"], 1)

    def test_distant_pfam_only_is_suppressed(self):
        db = database(raw_rows=[("FABRICATED", "fake", 9001, "FAKE_9001", "MOCK", 1, 1, 3, 2)], hit_rows=[("FAKE_9001", "fake", 1e-9, "fake", "pfam")])
        files, receipt = merge.render(db, coverage(db))
        self.assertEqual(files["distant.faa"], "")
        self.assertEqual(len(files["distant.txt"].splitlines()), 1)
        self.assertEqual(receipt["all_output_count"], 0)
        self.assertEqual(receipt["raw_input_count"], 1)

    def test_main_nohit_keeps_none_and_fasta(self):
        db = database()
        files, receipt = merge.render(db, coverage(db))
        self.assertTrue(files["out.txt"].splitlines()[1].endswith("\tnone\tnone\tnone"))
        self.assertEqual(files["out.faa"], ">RiPP|FAKE_1\nMOCK\n")
        self.assertEqual(receipt["all_output_count"], 1)

    def test_source_regex_is_not_every_id_starting_with_nine(self):
        db = database(raw_rows=[("FABRICATED", "fake", 900, "FAKE_900", "MOCK", 1, 1, 3, 2)])
        _, receipt = merge.render(db, coverage(db))
        self.assertEqual(receipt["main_output_count"], 1)

    def test_complete_empty_database_is_zero_with_headers(self):
        db = database(raw_rows=[])
        files, receipt = merge.render(db, coverage(db))
        self.assertEqual(receipt["raw_input_count"], 0)
        self.assertEqual(receipt["all_output_count"], 0)
        self.assertEqual(len(files["out.txt"].splitlines()), 1)

    def test_missing_and_failed_coverage_do_not_become_zero(self):
        for mode in ("missing", "FAILED", "NOT_RUN", "INTERRUPTED", "UNAVAILABLE"):
            with self.subTest(mode=mode):
                db = database()
                declared = coverage(db, None if mode == "missing" else mode)
                if mode == "missing":
                    declared["pairs"].pop()
                with self.assertRaisesRegex(merge.Refused, "MISSING_PAIR|ANNOTATION_INCOMPLETE"):
                    merge.render(db, declared)

    def test_nohit_contradicting_rows_refuses(self):
        db = database(hit_rows=[("FAKE_1", "fake", .01, "fake", "pfam")])
        declared = coverage(db)
        declared["pairs"][0]["state"] = "COMPLETE_NO_HIT"
        with self.assertRaisesRegex(merge.Refused, "PAIR_HIT_NOHIT_CONTRADICTION"):
            merge.render(db, declared)

    def test_ambiguous_best_hit_tie_holds(self):
        db = database(hit_rows=[("FAKE_1", "fake1", .01, "fake", "pfam"), ("FAKE_1", "fake2", .01, "fake", "ripp")])
        with self.assertRaisesRegex(merge.Refused, "AMBIGUOUS_BEST_HIT_TIE"):
            merge.render(db, coverage(db))

    def test_malformed_pair_types_refuse_with_a_typed_reason(self):
        for field in ("FastaID", "collection", "state"):
            with self.subTest(field=field):
                db = database()
                declared = coverage(db)
                declared["pairs"][0][field] = {"fabricated": "wrong type"}
                with self.assertRaisesRegex(merge.Refused, "PAIR_INVALID"):
                    merge.render(db, declared)

    def test_extra_unconsumed_sqlite_columns_do_not_change_merge(self):
        db = database(hit_rows=[("FAKE_1", "fake", .01, "fake", "pfam")])
        db.execute("alter table pfamscan add column extra_blob blob")
        db.execute("update pfamscan set extra_blob=?", (b"fabricated unrelated payload",))
        files, _ = merge.render(db, coverage(db))
        self.assertIn("fake", files["out.txt"])
        trace = json.loads(files["MERGE_TRACE.json"])
        self.assertNotIn("extra_blob", trace["rows"][0]["selected_hit"])

    def test_malformed_provenance_refuses_with_typed_reason(self):
        db = database()
        declared = coverage(db)
        declared["execution_provenance"] = {"fabricated": "invalid type"}
        with self.assertRaisesRegex(merge.Refused, "PROVENANCE_INVALID"):
            merge.render(db, declared)

    def test_sqlite_affinity_order_preserved_not_assumed_numeric(self):
        db = database("TEXT", hit_rows=[("FAKE_1", "lexical_first", "1e-3", "fake", "pfam"), ("FAKE_1", "numeric_smaller", "2e-9", "fake", "ripp")])
        files, receipt = merge.render(db, coverage(db))
        self.assertIn("lexical_first", files["out.txt"])
        self.assertEqual(receipt["hit_table_affinities"]["signif"], "TEXT")

    def test_duplicate_raw_ids_and_unknown_collection_refuse(self):
        row = ("FABRICATED", "fake", 1, "FAKE_1", "MOCK", 1, 1, 3, 2)
        db = database(raw_rows=[row, row])
        with self.assertRaisesRegex(merge.Refused, "AMBIGUOUS_RAW_FASTA_ID"):
            merge.render(db, coverage(db))
        db = database(hit_rows=[("FAKE_1", "fake", .01, "fake", "other")])
        with self.assertRaisesRegex(merge.Refused, "UNBOUND_HIT_QUERY_COLLECTION"):
            merge.render(db, coverage(db))


class FileExecution(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _init_tmp_path(self, tmp_path):
        self.fixture_root = tmp_path

    def inputs(self, name):
        root = self.fixture_root / name
        root.mkdir(parents=True)
        db = database(hit_rows=[("FAKE_1", "fake_model", .001, "fabricated model", "ripp")])
        declaration = coverage(db)
        disk = sqlite3.connect(root / "fabricated.sqlite3")
        db.backup(disk)
        disk.close()
        (root / "coverage.json").write_text(json.dumps(declaration))
        spec = {"raw_table": "ripper", "hit_table": "pfamscan"}
        for role, filename in (("database", "fabricated.sqlite3"), ("coverage", "coverage.json")):
            path = root / filename
            spec[role] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        (root / "spec.json").write_text(json.dumps(spec, indent=2))
        return root, spec

    def test_actual_readonly_sqlite_to_bound_outputs(self):
        root, spec = self.inputs("positive_sqlite_merge")
        before = Path(spec["database"]["path"]).read_bytes()
        result = merge.run(spec, root / "output")
        self.assertEqual(result["all_output_count"], 1)
        self.assertEqual(Path(spec["database"]["path"]).read_bytes(), before)
        self.assertTrue((root / "output/MERGE_RESULT.json").exists())
        for item in result["outputs"]:
            self.assertEqual(hashlib.sha256((root / "output" / item["name"]).read_bytes()).hexdigest(), item["sha256"])
        self.assertFalse(result["artifact_export_permission"])

    def test_actual_cli_failed_annotation_has_null_count(self):
        root, spec = self.inputs("cli_failed_annotation")
        path = Path(spec["coverage"]["path"])
        declared = json.loads(path.read_text())
        declared["pairs"][0]["state"] = "FAILED"
        path.write_text(json.dumps(declared))
        spec["coverage"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (root / "spec.json").write_text(json.dumps(spec, indent=2))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exitcode = merge.main(["--spec", str(root / "spec.json"), "--out", str(root / "output")])
        (root / "CLI_HOLD.json").write_text(stdout.getvalue())
        result = json.loads(stdout.getvalue())
        self.assertEqual(exitcode, 2)
        self.assertEqual(result["reason"], "ANNOTATION_INCOMPLETE")
        self.assertIsNone(result["candidate_count"])
        self.assertFalse((root / "output").exists())

    def test_changed_digest_and_sqlite_sidecar_refuse(self):
        root, spec = self.inputs("changed_binding")
        spec["database"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(merge.Refused, "INPUT_HASH_MISMATCH"):
            merge.run(spec, root / "output")
        self.assertFalse((root / "output").exists())
        root, spec = self.inputs("uncheckpointed_sidecar")
        Path(spec["database"]["path"] + "-wal").write_text("fabricated pending state")
        with self.assertRaisesRegex(merge.Refused, "SQLITE_SIDECAR_REFUSED"):
            merge.run(spec, root / "output")

    def test_failed_output_write_retains_staging_without_canonical_result(self):
        root, spec = self.inputs("writer_failure")
        original = merge.write_staging
        count = 0
        def fail_second(path, data):
            nonlocal count
            count += 1
            if count == 2:
                path.write_bytes(data[:2])
                raise OSError("fabricated writer interruption")
            return original(path, data)
        with patch.object(merge, "write_staging", fail_second):
            with self.assertRaisesRegex(OSError, "fabricated writer interruption"):
                merge.run(spec, root / "output")
        self.assertFalse((root / "output/MERGE_RESULT.json").exists())
        self.assertTrue((root / "output/out.txt.staging").exists())
        self.assertTrue((root / "output/out.faa.staging").exists())

    def test_final_link_failure_does_not_publish_result(self):
        root, spec = self.inputs("result_link_failure")
        link = os.link
        def fail_result(source, target):
            if Path(target).name == "MERGE_RESULT.json":
                raise OSError("fabricated final publication refusal")
            link(source, target)
        with patch.object(merge.os, "link", fail_result):
            with self.assertRaisesRegex(OSError, "fabricated final publication refusal"):
                merge.run(spec, root / "output")
        self.assertFalse((root / "output/MERGE_RESULT.json").exists())
        self.assertTrue((root / "output/MERGE_RESULT.json.staging").exists())




    def invoke_cli(self, spec, out):
        return subprocess.run([sys.executable, str(HERE.parents[1] / "tools/ripper_merge_e90.py"),
                               "--spec", str(spec), "--out", str(out)],
                              capture_output=True, timeout=15, check=False)

    def test_cli_success_exact_json_bytes_newline_exit_zero(self):
        root, spec = self.inputs("cli_success_protocol")
        db = sqlite3.connect(spec["database"]["path"])
        db.execute("update ripper set species=?", ("fabricated café 雪",))
        db.commit()
        db.close()
        spec["database"]["sha256"] = hashlib.sha256(Path(spec["database"]["path"]).read_bytes()).hexdigest()
        unicode_coverage = root / "café_雪.json"
        unicode_coverage.write_bytes(Path(spec["coverage"]["path"]).read_bytes())
        spec["coverage"]["path"] = str(unicode_coverage)
        (root / "spec.json").write_text(json.dumps(spec))
        result = self.invoke_cli(root / "spec.json", root / "output")
        expected = json.loads((root / "output/MERGE_RESULT.json").read_text())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout, (json.dumps(expected) + "\n").encode("utf-8"))
        self.assertEqual(result.stdout.count(b"\n"), 1)
        self.assertIn(b'caf\\u00e9', result.stdout)

    def test_cli_refusal_exact_json_bytes_newline_exit_two(self):
        root, spec = self.inputs("cli_refusal_protocol")
        path = Path(spec["coverage"]["path"])
        declared = json.loads(path.read_text())
        declared["pairs"][0]["state"] = "FAILED"
        path.write_text(json.dumps(declared))
        spec["coverage"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (root / "spec.json").write_text(json.dumps(spec))
        result = self.invoke_cli(root / "spec.json", root / "output")
        expected = {"state": "HOLD_OR_REFUSED", "reason": "ANNOTATION_INCOMPLETE", "candidate_count": None,
                    "annotation_execution": "NOT_OBSERVED_BY_MERGE_ADAPTER"}
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout, (json.dumps(expected) + "\n").encode("utf-8"))
        self.assertFalse((root / "output").exists())

    def test_cli_malformed_spec_exact_json_error_protocol(self):
        root, _ = self.inputs("cli_invalid_json_protocol")
        (root / "spec.json").write_text("{invalid")
        try:
            json.loads("{invalid")
        except json.JSONDecodeError as exc:
            reason = str(exc)
        result = self.invoke_cli(root / "spec.json", root / "output")
        expected = {"state": "HOLD_OR_REFUSED", "reason": reason, "candidate_count": None,
                    "annotation_execution": "NOT_OBSERVED_BY_MERGE_ADAPTER"}
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout, (json.dumps(expected) + "\n").encode("utf-8"))
        self.assertFalse((root / "output").exists())

    def test_cli_encoder_failure_precedes_any_output(self):
        root, _ = self.inputs("cli_encoder_failure")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(merge, "run", return_value={"unserializable": object()}):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                with self.assertRaises(TypeError):
                    merge.main(["--spec", str(root / "spec.json"), "--out", str(root / "output")])
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_cli_stream_error_propagates_success_and_refusal(self):
        root, _ = self.inputs("cli_stream_failure")
        class ClosedPipe(io.StringIO):
            def write(self, value):
                raise BrokenPipeError("fabricated closed JSON stream")
        for refused in (False, True):
            with self.subTest(refused=refused):
                kwargs = {"side_effect": merge.Refused("fabricated refusal")} if refused else {"return_value": {"state": "fabricated"}}
                with patch.object(merge, "run", **kwargs), contextlib.redirect_stdout(ClosedPipe()):
                    with self.assertRaisesRegex(BrokenPipeError, "fabricated closed JSON stream"):
                        merge.main(["--spec", str(root / "spec.json"), "--out", str(root / "output")])


def comparison_database(ids, hits, qname_type="TEXT", significance_type="REAL"):
    db = sqlite3.connect(":memory:")
    db.execute("create table ripper(acc text,species text,ppser integer,fastaid text,aaseq text,ppstrand integer,testrand integer,pptedist integer,score real,unique(acc,ppser))")
    db.execute("create table pfamscan(qname " + qname_type + ",hname text,signif " + significance_type + ",hdesc text,collection text)")
    for index, fid in enumerate(ids):
        db.execute("insert into ripper values(?,?,?,?,?,?,?,?,?)", ("FABRICATED", "fabricated comparison fixture", index, fid, "MOCK", 1, 1, 7, 3.5))
    db.executemany("insert into pfamscan values(?,?,?,?,?)", hits)
    declared = {"schema": "ripper-annotation-coverage-proposal/1", "execution_provenance": "FABRICATED_SOFTWARE_CONTROL",
                "pairs": [{"FastaID": fid, "collection": collection,
                           "state": "COMPLETE_HIT" if any(hit[0] == fid and hit[4] == collection for hit in hits) else "COMPLETE_NO_HIT"}
                          for fid in ids for collection in ("pfam", "ripp")]}
    return db, declared


class SQLiteComparisons(unittest.TestCase):
    def test_nocase_query_join_keeps_exact_nohit_main_and_distant(self):
        for suffix in ("", "_9001"):
            with self.subTest(suffix=suffix):
                upper, lower = "CaseID" + suffix, "caseid" + suffix
                collection = "ripp" if suffix else "pfam"
                db, declared = comparison_database([upper, lower], [(upper, "upper_only", .001, "fabricated", collection)], qname_type="TEXT COLLATE NOCASE")
                files, receipt = merge.render(db, declared)
                rows = {row["FastaID"]: row for row in json.loads(files["MERGE_TRACE.json"])["rows"]}
                self.assertEqual(rows[upper]["selected_hit"]["qname"], upper)
                self.assertIsNone(rows[lower]["selected_hit"])
                self.assertEqual(rows[lower]["admitted"], not bool(suffix))
                self.assertEqual(receipt["all_output_count"], 1 if suffix else 2)

    def test_nocase_significance_sql_peers_hold_both_orders_main_and_distant(self):
        for suffix in ("", "_9001"):
            for reverse in (False, True):
                with self.subTest(suffix=suffix, reverse=reverse):
                    fid = "FAKE" + suffix
                    hits = [(fid, "first", "1e-3", "fabricated", "ripp" if suffix else "pfam"), (fid, "second", "1E-3", "fabricated", "ripp")]
                    if reverse:
                        hits.reverse()
                    db, declared = comparison_database([fid], hits, significance_type="TEXT COLLATE NOCASE")
                    with self.assertRaisesRegex(merge.Refused, "AMBIGUOUS_BEST_HIT_TIE"):
                        merge.render(db, declared)

    def test_distinct_nocase_significance_preserves_lexical_order(self):
        for suffix in ("", "_9001"):
            for reverse in (False, True):
                with self.subTest(suffix=suffix, reverse=reverse):
                    fid = "FAKE" + suffix
                    hits = [(fid, "lexical_first", "1e-3", "fabricated", "ripp" if suffix else "pfam"), (fid, "numeric_smaller", "9e-4", "fabricated", "ripp")]
                    if reverse:
                        hits.reverse()
                    db, declared = comparison_database([fid], hits, significance_type="TEXT COLLATE NOCASE")
                    files, _ = merge.render(db, declared)
                    selected = json.loads(files["MERGE_TRACE.json"])["rows"][0]["selected_hit"]
                    self.assertEqual(selected["hname"], "lexical_first")

    def test_rtrim_significance_sql_peers_hold_both_orders_main_and_distant(self):
        for suffix in ("", "_9001"):
            for reverse in (False, True):
                with self.subTest(suffix=suffix, reverse=reverse):
                    fid = "FAKE" + suffix
                    hits = [(fid, "first", "1e-3", "fabricated", "ripp" if suffix else "pfam"), (fid, "second", "1e-3 ", "fabricated", "ripp")]
                    if reverse:
                        hits.reverse()
                    db, declared = comparison_database([fid], hits, significance_type="TEXT COLLATE RTRIM")
                    with self.assertRaisesRegex(merge.Refused, "AMBIGUOUS_BEST_HIT_TIE"):
                        merge.render(db, declared)

    def test_real_significance_equal_and_unequal_use_sql_order(self):
        for suffix in ("", "_9001"):
            for reverse in (False, True):
                for equal in (False, True):
                    with self.subTest(suffix=suffix, reverse=reverse, equal=equal):
                        fid = "FAKE" + suffix
                        hits = [(fid, "best", .001, "fabricated", "ripp" if suffix else "pfam"), (fid, "other", .001 if equal else .002, "fabricated", "ripp")]
                        if reverse:
                            hits.reverse()
                        db, declared = comparison_database([fid], hits)
                        if equal:
                            with self.assertRaisesRegex(merge.Refused, "AMBIGUOUS_BEST_HIT_TIE"):
                                merge.render(db, declared)
                        else:
                            files, _ = merge.render(db, declared)
                            self.assertEqual(json.loads(files["MERGE_TRACE.json"])["rows"][0]["selected_hit"]["hname"], "best")

    def test_binary_text_case_variants_do_not_become_numeric_tie(self):
        for suffix in ("", "_9001"):
            for reverse in (False, True):
                with self.subTest(suffix=suffix, reverse=reverse):
                    fid = "FAKE" + suffix
                    hits = [(fid, "uppercase", "1E-3", "fabricated", "ripp" if suffix else "pfam"), (fid, "lowercase", "1e-3", "fabricated", "ripp")]
                    if reverse:
                        hits.reverse()
                    db, declared = comparison_database([fid], hits, significance_type="TEXT")
                    files, _ = merge.render(db, declared)
                    self.assertEqual(json.loads(files["MERGE_TRACE.json"])["rows"][0]["selected_hit"]["hname"], "uppercase")

    def test_query_cohorts_do_not_create_foreign_significance_peers(self):
        for suffix in ("", "_9001"):
            with self.subTest(suffix=suffix):
                upper, lower = "CaseID" + suffix, "caseid" + suffix
                collection = "ripp" if suffix else "pfam"
                hits = [(upper, "upper", "1e-3", "fabricated", collection), (lower, "lower", "1E-3", "fabricated", collection)]
                db, declared = comparison_database([upper, lower], hits, qname_type="TEXT COLLATE NOCASE", significance_type="TEXT COLLATE NOCASE")
                files, _ = merge.render(db, declared)
                rows = json.loads(files["MERGE_TRACE.json"])["rows"]
                self.assertEqual([row["selected_hit"]["qname"] for row in rows], [upper, lower])
