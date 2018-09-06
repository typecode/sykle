import subprocess
import os


def call_subprocess(command, docker_vars=None, debug=False):
    env = None
    parsed_docker_vars = {}
    if docker_vars:
        for (k, v) in docker_vars.items():
            if v[0] == '$':
                parsed_docker_vars[k] = os.environ.get(v[1:])
            else:
                parsed_docker_vars[k] = v
        env = os.environ.copy()
        env.update(parsed_docker_vars)

    if debug:
        print('--BEGIN COMMAND--')
        print('COMMAND:', ' '.join(command))
        if docker_vars:
            print('DOCKER VARS:', parsed_docker_vars)
        print('--END COMMAND--')

    if parsed_docker_vars:
        subprocess.call(command, env=env)
    else:
        subprocess.call(command)
