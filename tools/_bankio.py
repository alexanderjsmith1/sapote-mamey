"""Banked tool read/write boundary; delegates journal checks and lock ownership."""
from pathlib import Path
import sys
def _transaction_api():
    """Resolve the bundle API; temporarily admit the root for bare-tool imports."""
    try:
        from mamey import bank_transaction
    except ModuleNotFoundError as error:
        if error.name != 'mamey':
            raise
        root = str(Path(__file__).resolve().parent.parent)
        sys.path.insert(0, root)
        try:
            from mamey import bank_transaction
        finally:
            sys.path.pop(0)
    return bank_transaction


_api = _transaction_api()
hold_reader = _api.hold_reader
release_reader_locks = _api.release_reader_locks
reader = _api.reader
lock = _api.lock
prepare = _api.prepare
coherent = _api.coherent
BankError = _api.BankError
STORES = _api.STORES

def checked_json(path, encoding='utf-8'):
    import json
    with reader(Path(path).parent):
        with open(path,encoding=encoding) as handle:return json.load(handle)

def transactional_call(bank, callback):
    import contextlib, io
    captured=io.StringIO()
    with lock(bank,writer=True) as root:
        coherent(root)
        def build(stage):
            with contextlib.redirect_stdout(captured):
                code=callback(stage)
            if code not in (None,0):raise BankError('BANK_STAGE_CALLBACK_FAILED: '+str(code))
        prepare(root,build,STORES+('deep_data.json',))
    sys.stdout.write(captured.getvalue())
    return 0
