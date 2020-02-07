import os
import traceback
import subprocess as _subprocess
from functools import wraps
from contextlib import ContextDecorator
from sykle.config import Config


class CancelException(Exception):
    pass


class NonZeroReturnCodeException(Exception):
    def __init__(self, process, stacktrace='', command=''):
        self.process = process
        self.message = 'Process returned a non zero returncode'
        self.stacktrace = ''.join(stacktrace)
        self.command = command

    def __str__(self):
        return self.message


def call_subprocess(command, env=None, debug=False, target=None):
    """
    This is a utility function that will spawn a subprocess that runs the
    command passed in to the command argument.

    Parameters:
        command (array[str]): the command to run as a subprocess
        env (dict): an optional dictionary of env vars to specify for command.
                    values in env can references local environment variables.
                    EX: env can be {'TEST': '$TEST_VAL'}
        debug (bool): if true, will output the command as given and the env
                      vars used
        target (string): an optional ssh address specifying where to run the
                         command (runs locally if not specified)
                         NOTE: env vars will be interpolated based on LOCAL
                               environment variables, not TARGET environment
                               variables.
    """
    if env:
        # NB: we want the entire environment specified here
        full_env = os.environ.copy()
        env = Config.interpolate_env_values(env, os.environ)
        full_env.update(env)

    cmd = command
    if target:
        if env:
            cmd = ["{}={}".format(k, v) for k, v in env.items()] + cmd
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', target] + cmd

    full_command = ' '.join(cmd)

    if debug:
        print('--BEGIN COMMAND--')
        print('COMMAND:', full_command)
        print('--END COMMAND--')

    try:
        if env:
            p = _subprocess.Popen(full_command, env=full_env, shell=True)
        else:
            p = _subprocess.Popen(full_command, shell=True)
        p.wait()

        if p.returncode != 0:
            raise NonZeroReturnCodeException(
                process=p, stacktrace=traceback.format_stack(),
                command=full_command
            )
    except KeyboardInterrupt:
        p.wait()
        raise CancelException()


class SubprocessContext(ContextDecorator):
    """Wraps the `call_subprocess` function for use as a context
    decorator."""
    def __enter__(self, *args, **kwargs):
        pass

    def __call__(self, get_cmd):
        @wraps(get_cmd)
        def inner(*args, **kwargs):
            with self._recreate_cm():
                cmd = get_cmd(*args, **kwargs)
                return call_subprocess(cmd)
        return inner

    def __exit__(self, *args):
        pass


class SubprocessExceptionHandler:
    """Utility for collecting exceptions and raising a `SystemExit`
    exception with those exceptions' stacktraces. Ex:

        exception_handler = SubprocessExceptionHandler()

        for subprocess in subprocesses_that_throw_exceptions:
            try:
                subprocess()
            except NonZeroReturnCodeException as e:
                exception_handler.push(e)

        exception_handler.exit_with_stacktraces()
    """
    def __init__(self):
        self.exc_stack = []

    def push(self, exc):
        self.exc_stack.append(exc)

    def exit_with_stacktraces(self):
        # Gather the errors' stack traces and return
        # them in a single final error.
        if len(self.exc_stack):
            stacktraces = '\n'.join([
                '%s\n%s' % (exc.command, exc.stacktrace)
                for exc in self.exc_stack
            ])

            # Status code defaults to 1 when we pass a string.
            raise SystemExit(stacktraces)


subprocess = SubprocessContext()
