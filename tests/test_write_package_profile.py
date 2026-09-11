import inspect
import mamey.cli as cli

def test_write_package_accepts_referenced_run_params():
    """Regression (build -q): _write_package referenced `antismash_profile` in its body without
    accepting it as a parameter -> NameError at package-write on EVERY real `mamey run`. The unit
    suite missed it because nothing exercised the run->package path. Guard: any run-scoped name used
    in the writer body must be a parameter (else it is a runtime NameError)."""
    params = set(inspect.signature(cli._write_package).parameters)
    src = inspect.getsource(cli._write_package)
    for name in ("antismash_profile",):
        if name in src:
            assert name in params, f"_write_package uses {name!r} but does not accept it (runtime NameError)"
