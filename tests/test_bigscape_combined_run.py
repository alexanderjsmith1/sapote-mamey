"""
test_bigscape_combined_run.py — Sapote-Mamey BiG-SCAPE combined-run tests patch tests

Tests the five-fix GBK reconstruction that makes combined BiG-SCAPE runs
possible from a pre-existing DB + new strain GBKs.
"""

import os
import sqlite3
import tempfile

import pytest
SeqIO = pytest.importorskip("Bio.SeqIO")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_test_db(path, n_gbks=3, include_zero_start=True):
    """Create a minimal BiG-SCAPE 2-like SQLite DB for testing."""
    db = sqlite3.connect(path)
    cur = db.cursor()
    cur.execute(
        "CREATE TABLE gbk (id INTEGER PRIMARY KEY, path TEXT, hash TEXT, "
        "nt_seq TEXT, organism TEXT, taxonomy TEXT, description TEXT)"
    )
    cur.execute(
        "CREATE TABLE cds (id INTEGER PRIMARY KEY, gbk_id INTEGER, "
        "nt_start INTEGER, nt_stop INTEGER, orf_num INTEGER, "
        "strand INTEGER, gene_kind TEXT, aa_seq TEXT)"
    )
    cur.execute(
        "CREATE TABLE bgc_record (id INTEGER PRIMARY KEY, gbk_id INTEGER, "
        "parent_id INTEGER, record_number INTEGER, contig_edge BOOLEAN, "
        "record_type TEXT, nt_start INTEGER, nt_stop INTEGER, "
        "product TEXT, category TEXT, merged BOOLEAN)"
    )

    cds_id = 1
    for i in range(1, n_gbks + 1):
        seq = "ATGC" * 500  # 2000 bp
        name = f"TestStrain_NODE_{i}_length_2000_cov_50.region001.gbk"
        cur.execute(
            "INSERT INTO gbk VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i, f"/fake/path/{name}", f"hash_{i}", seq, "Streptomyces griseus subsp. griseus", "Bacteria", name),
        )
        # Region record
        cur.execute(
            "INSERT INTO bgc_record VALUES (?, ?, NULL, 1, 0, 'region', 0, 2000, 'T1PKS', 'PKS', 0)",
            (i, i),
        )
        # CDS: first one starts at 0 (the bug) if include_zero_start
        start0 = 0 if include_zero_start else 1
        cur.execute(
            "INSERT INTO cds VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (cds_id, i, start0, 300, 1, 1, "biosynthetic", "MTTAHKIL" * 10),
        )
        cds_id += 1
        cur.execute(
            "INSERT INTO cds VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (cds_id, i, 400, 900, 2, -1, "regulatory", "MVQNILLS" * 8),
        )
        cds_id += 1

    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGBKReconstruction:
    """Test the five fixes in reconstruct_gbks."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.out_dir = os.path.join(self.tmpdir, "reconstructed")
        make_test_db(self.db_path)

    def _reconstruct(self, **kwargs):
        # Import inline so the test works without the full bundle on PATH
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "bigscape_combined_run",
            os.path.join(os.path.dirname(__file__), "..", "tools", "bigscape_combined_run.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.reconstruct_gbks(self.db_path, self.out_dir, **kwargs)

    def test_fix1_locus_line_no_crash(self):
        """Fix 1: long organism names don't break the LOCUS line."""
        n = self._reconstruct()
        assert n == 3
        for f in os.listdir(self.out_dir):
            if not f.endswith(".gbk"):
                continue
            with open(os.path.join(self.out_dir, f)) as fh:
                line = fh.readline()
                assert line.startswith("LOCUS")
                # Locus name must be ≤ 16 chars (GenBank spec)
                parts = line.split()
                assert len(parts[1]) <= 16, f"Locus name too long: {parts[1]}"

    def test_fix2_no_zero_coordinates(self):
        """Fix 2: CDS coordinates are 1-based, never 0."""
        self._reconstruct()
        for f in os.listdir(self.out_dir):
            if not f.endswith(".gbk"):
                continue
            with open(os.path.join(self.out_dir, f)) as fh:
                content = fh.read()
                # No "0.." pattern in CDS locations
                import re
                zero_locs = re.findall(r"CDS\s+(?:complement\()?0\.\.", content)
                assert len(zero_locs) == 0, f"Found 0-based coordinate in {f}: {zero_locs}"

    def test_fix2_biopython_parses_all_cds(self):
        """Fix 2: BioPython can parse every CDS without NoneType.start."""
        self._reconstruct()
        for f in os.listdir(self.out_dir):
            if not f.endswith(".gbk"):
                continue
            path = os.path.join(self.out_dir, f)
            records = list(SeqIO.parse(path, "genbank"))
            assert len(records) == 1
            for feat in records[0].features:
                if feat.type == "CDS":
                    # This is the exact line that crashed: feat.location.start
                    assert feat.location is not None, f"CDS location is None in {f}"
                    assert feat.location.start is not None
                    assert feat.location.start >= 0

    def test_fix3_no_antismash_features(self):
        """Fix 3: reconstructed GBKs have no antiSMASH region/cand_cluster features."""
        self._reconstruct()
        for f in os.listdir(self.out_dir):
            if not f.endswith(".gbk"):
                continue
            path = os.path.join(self.out_dir, f)
            records = list(SeqIO.parse(path, "genbank"))
            for feat in records[0].features:
                assert feat.type not in ("region", "cand_cluster", "protocluster"), \
                    f"Found {feat.type} feature in reconstructed GBK {f}"

    def test_exclude_strain(self):
        """exclude_strain filters out matching GBKs."""
        # Add a strain to exclude
        db = sqlite3.connect(self.db_path)
        cur = db.cursor()
        cur.execute(
            "INSERT INTO gbk VALUES (99, '/fake/AS-846_NODE_1.gbk', 'h99', 'ATGC', '.', '.', 'AS-846')"
        )
        cur.execute(
            "INSERT INTO cds VALUES (99, 99, 100, 400, 1, 1, 'biosynthetic', 'MTEST')"
        )
        db.commit()
        db.close()

        n = self._reconstruct(exclude_strain="AS-846")
        assert n == 3  # the 3 original, not the AS-846 one
        fnames = os.listdir(self.out_dir)
        assert not any("AS-846" in f for f in fnames)

    def test_cds_translation_present(self):
        """CDS features carry /translation with the amino acid sequence."""
        self._reconstruct()
        for f in os.listdir(self.out_dir):
            if not f.endswith(".gbk"):
                continue
            path = os.path.join(self.out_dir, f)
            records = list(SeqIO.parse(path, "genbank"))
            cds_count = 0
            for feat in records[0].features:
                if feat.type == "CDS":
                    cds_count += 1
                    assert "translation" in feat.qualifiers, f"No translation in CDS in {f}"
                    assert len(feat.qualifiers["translation"][0]) > 0
            assert cds_count == 2, f"Expected 2 CDS in {f}, got {cds_count}"

    def test_origin_sequence_present(self):
        """ORIGIN section has the full nucleotide sequence."""
        self._reconstruct()
        for f in os.listdir(self.out_dir):
            if not f.endswith(".gbk"):
                continue
            path = os.path.join(self.out_dir, f)
            records = list(SeqIO.parse(path, "genbank"))
            assert len(records[0].seq) == 2000  # 4 * 500

    def test_complement_strand(self):
        """Negative-strand CDS uses complement() location."""
        self._reconstruct()
        for f in os.listdir(self.out_dir):
            if not f.endswith(".gbk"):
                continue
            with open(os.path.join(self.out_dir, f)) as fh:
                content = fh.read()
                assert "complement(" in content, f"No complement strand in {f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
