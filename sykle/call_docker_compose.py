import dotenv
from .call_subprocess import call_subprocess


def docker_compose_file_for_type(type):
    if type == 'dev':
        return './docker-compose.yml'
    elif type == 'test':
        return './docker-compose.test.yml'
    elif type == 'prod-build':
        return './docker-compose.prod-build.yml'
    elif type == 'prod':
        return './docker-compose.prod.yml'


def call_docker_compose(
    input, type='dev', project_name='tc-project',
    debug=False, docker_vars={}, target=None, env_file=None
):
    dc_file = docker_compose_file_for_type(type)

    opts = []
    project_command = []
    project_command = ['-p', '{}-{}'.format(project_name, type)]

    if env_file:
        # NB: as of this comment, docker-compose does not have an
        #     --env-file option. If it did, we would use it here.
        #     See: https://github.com/docker/compose/issues/6170
        env = dotenv.dotenv_values(env_file)
        if input[0] == 'build':
            opts = []
            for k, v in env.items():
                opts.append('--build-arg')
                opts.append('\"{}={}\"'.format(k, v))
            input = [input[0]] + opts + input[1:]
        elif input[0] == 'run':
            opts = []
            for k, v in env.items():
                opts.append('-e')
                opts.append('\"{}={}\"'.format(k, v))
            input = [input[0]] + opts + input[1:]

    return call_subprocess(
        ['docker compose'] + project_command + ['-f', dc_file] + input,
        debug=debug, env=docker_vars, target=target
    )
