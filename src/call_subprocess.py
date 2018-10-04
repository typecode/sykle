import subprocess
import os
from src.config import Config


def call_subprocess(command, env=None, debug=False):
    full_env = os.environ.copy()
    full_command = ' '.join(command)

    if env:
        env = Config.interpolate_env_values(env, os.environ)
        full_env.update(env)

    if debug:
        print('--BEGIN COMMAND--')
        print('COMMAND:', full_command)
        if env:
            print('ENV:', env)
        print('--END COMMAND--')

    if env:
        subprocess.call(full_command, env=full_env, shell=True)
    else:
        subprocess.call(full_command, shell=True)
