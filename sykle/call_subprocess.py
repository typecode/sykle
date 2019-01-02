import subprocess
import os
from sykle.config import Config


def call_subprocess(command, env=None, debug=False, target=None):
    if env:
        full_env = os.environ.copy()
        env = Config.interpolate_env_values(env, os.environ)
        full_env.update(env)

    if target:
        if env:
            command = ["{}={}".format(k, v) for k, v in env.items()] + command
        command = ['ssh', '-o', 'StrictHostKeyChecking=no', target] + command

    full_command = ' '.join(command)

    if debug:
        print('--BEGIN COMMAND--')
        print('COMMAND:', full_command)
        if env:
            print('ENV:', env)
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
        return p
