"""NCBI submission cadence (v9.7.382): run_batches_online spaces Puts >= 10s per NCBI URL-API rules."""
import inspect
from mamey import blastp_online


def test_submit_gap_default_is_at_least_10s():
    sig = inspect.signature(blastp_online.run_batches_online)
    assert sig.parameters["submit_gap_seconds"].default >= 10, \
        "NCBI BLAST URL-API asks for >=10s between server contacts; the submit gap default must be >= 10"
