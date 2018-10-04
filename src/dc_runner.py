import subprocess
from .call_subprocess import call_subprocess


class DCRunner():
    """
    Class for running a docker compose project
    """
    def __init__(
        self,
        type='dev', project_name='tc-project',
        debug=False, docker_vars={}
    ):
        self.type = type
        self.project_name = project_name
        self.debug = debug
        self.docker_vars = docker_vars

    @property
    def docker_compose_file(self):
        """Returns the docker compose file that should be used"""
        if self.type == 'dev':
            return './docker-compose.yml'
        elif self.type == 'test':
            return './docker-compose.test.yml'
        elif self.type == 'prod-build':
            return './docker-compose.prod-build.yml'
        elif self.type == 'prod':
            return './docker-compose.prod.yml'

    @property
    def project_command(self):
        if self.type == 'prod' or self.type == 'prod-build':
            return ['-p', self.project_name]
        return ['-p', '{}-{}'.format(self.project_name, self.type)]

    def call(self, input):
        base_command = (
            ['docker-compose'] +
            self.project_command +
            ['-f', self.docker_compose_file]
        )

        try:
            call_subprocess(
                base_command + input,
                debug=self.debug,
                env=self.docker_vars
            )
        except KeyboardInterrupt:
            print('Exiting...')
            subprocess.call(base_command + ['down'])
