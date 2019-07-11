import subprocess
import os
from sykle.config import Config


class CancelException(Exception):
    pass


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
            p = subprocess.Popen(full_command, env=full_env, shell=True)
        else:
            p = subprocess.Popen(full_command, shell=True)
        p.wait()
        return p
    except KeyboardInterrupt:
        p.wait()
        raise CancelException()
