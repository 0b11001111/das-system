# Standard library modules.
import io
import sys
import time
import traceback
import subprocess
from functools import partial
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from tempfile import NamedTemporaryFile

# Third party modules.

# Local modules

# Globals and constants variables.


@contextmanager
def timeout(timeout_):
    start = time.time()

    # trace callbacks
    def _globaltrace(frame, event, arg):
        return _localtrace if event == 'call' else None

    def _localtrace(frame, event, arg):
        if time.time() - start >= timeout_ and event == 'line':
            raise TimeoutError(f'code execution took longer than {timeout_:.3f}s to terminate')

    # activate tracing only in case timeout was actually set
    if timeout_:
        sys.settrace(_globaltrace)

    try:
        yield start

    finally:
        sys.settrace(None)


def sandboxed_exec(code, timeout_=None, namespace=None):
    state = dict(__EXCEPTION__=None)

    if namespace:
        state.update(namespace)

    with io.StringIO() as stdout, io.StringIO() as stderr:
        with redirect_stdout(stdout), redirect_stderr(stderr), timeout(timeout_):
            try:
                exec(code, state)

            except Exception as e:
                state['__EXCEPTION__'] = type(e)
                traceback.print_exception(type(e), e, e.__traceback__, file=stderr)

        state['__STDOUT__'] = stdout.getvalue()
        state['__STDERR__'] = stderr.getvalue()

    return state


@contextmanager
def tts(txt):
    with NamedTemporaryFile() as f:
        cmd = f'espeak -v de -k 5 -s 150 -w {f.name}'.split()
        assert not subprocess.run(cmd + [txt]).returncode

        yield f
