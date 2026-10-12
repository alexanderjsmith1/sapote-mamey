"""Fresh-process logging compatibility and import-state regressions."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def fresh_logger(tmp_path):
    source = Path(__file__).resolve().parents[1] / 'mamey/logging_setup.py'
    package = tmp_path / 'mamey'
    package.mkdir()
    (package / '__init__.py').write_text('')
    shutil.copy2(source, package / 'logging_setup.py')

    def run(body, level='info'):
        env = dict(os.environ, PYTHONPATH=str(tmp_path), PYTHONDONTWRITEBYTECODE='1', MAMEY_LOG=level)
        result = subprocess.run([sys.executable, '-c', body], cwd=tmp_path, env=env,
                                text=True, capture_output=True, timeout=15)
        assert result.returncode == 0, result.stderr
        assert result.stderr == ''
        return json.loads(result.stdout)
    return run


def test_factory_preserves_standard_identity_without_configuring_handlers(fresh_logger):
    got = fresh_logger('''
import json,logging
from mamey import logging_setup as ls
root=logging.getLogger('mamey')
before=(list(root.handlers),root.level,root.propagate)
one=ls.get_logger('mamey.example');two=ls.get_logger('example')
assert one is two is logging.getLogger('mamey.example')
assert isinstance(one,logging.Logger)
assert before==(list(root.handlers),root.level,root.propagate)
assert not ls._configured
print(json.dumps({'identity':True,'unconfigured':True}))
''')
    assert got == {'identity': True, 'unconfigured': True}


@pytest.mark.parametrize('level,expected', [('info', 'hello [test]\n'), ('warning', ''), ('debug', 'hello [test]\n')])
def test_first_message_uses_environment_filter_and_current_stdout(fresh_logger, level, expected):
    got = fresh_logger('''
import contextlib,io,json
from mamey import logging_setup as ls
log=ls.get_logger('example');buf=io.StringIO()
with contextlib.redirect_stdout(buf): log.info('hello [test]')
print(json.dumps({'text':buf.getvalue(),'configured':ls._configured}))
''', level)
    assert got == {'text': expected, 'configured': True}


def test_first_debug_is_filtered_and_later_capture_follows_stdout(fresh_logger):
    got = fresh_logger('''
import contextlib,io,json
from mamey import logging_setup as ls
log=ls.get_logger('example');a=io.StringIO();b=io.StringIO()
with contextlib.redirect_stdout(a):
    log.debug('hidden')
    log.warning('first')
with contextlib.redirect_stdout(b): log.info('second')
print(json.dumps([a.getvalue(),b.getvalue()]))
''')
    assert got == ['first\n', 'second\n']


def test_explicit_configuration_and_custom_child_handler_remain_supported(fresh_logger):
    got = fresh_logger('''
import io,json,logging
from mamey import logging_setup as ls
log=ls.get_logger('example');a=io.StringIO();b=io.StringIO()
handler=logging.StreamHandler(b);log.addHandler(handler)
ls.configure('debug',fmt='%(levelname)s: %(message)s',stream=a)
log.debug('visible')
log.removeHandler(handler)
ls.configure('warning',stream=a);log.info('hidden');log.error('error')
print(json.dumps([a.getvalue(),b.getvalue()]))
''')
    assert got == ['DEBUG: visible\nerror\n', 'visible\n']


def test_reload_retains_logger_and_first_message_does_not_duplicate(fresh_logger):
    got = fresh_logger('''
import contextlib,importlib,io,json,logging
from mamey import logging_setup as ls
log=ls.get_logger('example');buf=io.StringIO()
with contextlib.redirect_stdout(buf): log.info('before')
importlib.reload(ls)
assert log is ls.get_logger('example')
with contextlib.redirect_stdout(buf): log.info('after')
root=logging.getLogger('mamey')
print(json.dumps({'text':buf.getvalue(),'owned_handlers':sum(h.get_name()=='mamey-default' for h in root.handlers)}))
''')
    assert got == {'text': 'before\nafter\n', 'owned_handlers': 1}


def test_concurrent_first_messages_configure_once(fresh_logger):
    got = fresh_logger('''
import io,json,logging,threading
from mamey import logging_setup as ls
log=ls.get_logger('example');buf=io.StringIO()
import contextlib
barrier=threading.Barrier(8)
def send():
    barrier.wait();log.info('once')
threads=[threading.Thread(target=send) for _ in range(8)]
with contextlib.redirect_stdout(buf):
    for thread in threads: thread.start()
    for thread in threads: thread.join()
root=logging.getLogger('mamey')
print(json.dumps({'lines':buf.getvalue().splitlines(),'owned_handlers':sum(h.get_name()=='mamey-default' for h in root.handlers)}))
''')
    assert got == {'lines': ['once'] * 8, 'owned_handlers': 1}
