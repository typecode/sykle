from .call_subprocess import call_subprocess


def docker_compose_file_for_type(self, type):
    if type == 'dev':
        return './docker-compose.yml'
    elif type == 'test':
        return './docker-compose.test.yml'
    elif type == 'prod-build':
        return './docker-compose.prod-build.yml'
    elif type == 'prod':
        return './docker-compose.prod.yml'


def project_name_for_type(self, type):
    if type == 'prod' or type == 'prod-build':
        return ['-p', '{}-{}'.format(self.project_name, self.type)]


def call_docker_compose(
    input, type='dev', project_name='tc-project',
    debug=False, docker_vars={}, target=None
):
    prod = type == 'prod' or type == 'prod-build'
    dc_file = docker_compose_file_for_type(type)
    project_name = project_name if prod else '{}-{}'.format(project_name, type)
    return call_subprocess(
        ['docker-compose', '-p', project_name, '-f', dc_file] + input,
        debug=debug, env=docker_vars, target=target
    )
