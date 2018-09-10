from .dc_runner import DCRunner
from .call_subprocess import call_subprocess


class Sykle():
    """
    Class for programatically invoking Sykle
    """
    def __init__(
        self, deployment_target=None,
        project_name='sykle-project',
        unittest_config=[], e2e_config=[],
        predeploy_config=[], debug=False,
        docker_vars={}, aliases={}
    ):
        """
        Parameters:
            debug (bool): Set to true to print debug information
            project_name (str): Name of the entire project
            unittest_config (array[dict]): Array of unittest configs
            e2e_config (array[dict]): Array of end to end test configs
            predeploy_config (array[dict]): Array with predeploy steps
            deployment_target (str): SSH address of deployment target
            aliases (dict): Dictionary defining custom commands
            docker_vars (str): Vars used in docker-compose/docker files
        """
        self.aliases = aliases
        self.debug = debug
        self.project_name = project_name
        self.docker_vars = docker_vars
        self.e2e_config = e2e_config
        self.predeploy_config = predeploy_config
        self.unittest_config = unittest_config
        # NB: we ONLY want throw errors for these varialbes if they're USED
        self._deployment_target = deployment_target

    @property
    def deployment_target(self):
        """Throws error if there is no deployment target"""
        if not self._deployment_target:
            raise Exception('No deployment target found!')
        return self._deployment_target

    @property
    def docker_vars_command(self):
        return ["{}={}".format(k, v) for k, v in self.docker_vars.items()]

    def _run_tests(self, configs, warning=None, input=[], service=None):
        if not configs and warning:
            print(warning)
            return

        self.build(docker_type='test')
        for config in configs:
            if service and (config['service'] != service):
                continue
            command = config['command'].split(' ') + input
            self.dc_run(command, service=config['service'], docker_type='test')
        self.down(docker_type='test')

    def dc(self, input, docker_type='dev', docker_vars={}):
        """Runs a command with the correct docker compose file(s)"""
        _docker_vars = self.docker_vars.copy()
        _docker_vars.update(docker_vars)
        DCRunner(
            type=docker_type,
            project_name=self.project_name,
            debug=self.debug,
            docker_vars=_docker_vars,
        ).call(input)

    def dc_run(self, input, service=None, docker_type='dev'):
        """Runs a command in a docker compose service"""
        self.dc(
            input=['run', '--rm', service or self.default_service] + input,
            docker_type=docker_type,
        )

    def build(self, docker_type='dev'):
        """Builds docker images based on compose files"""
        if docker_type == 'prod':
            self.dc(
                input=['build'],
                docker_type='prod-build'
            )
            self.dc(
                input=['build'],
                docker_type='prod-build',
                docker_vars={'BUILD_NUMBER': 'latest'}
            )
        else:
            self.dc(
                input=['build'],
                docker_type=docker_type
            )

    def up(self, docker_type='dev'):
        """Starts up relevant docker compose services"""
        self.dc(
            input=['up', '--build'],
            docker_type=docker_type
        )

    def down(self, docker_type='dev'):
        """Spins down relevant docker compose services"""
        self.dc(
            input=['down'],
            docker_type=docker_type
        )

    def unittest(self, input=[], service=None):
        self._run_tests(
            self.unittest_config,
            warning='No unittests configured!',
            input=input, service=None
        )

    def e2e(self, input=[], service=None):
        self._run_tests(
            self.e2e_config,
            warning='No end to end tests configured!',
            input=input, service=None
        )

    def push(self):
        """Pushes docker images"""
        self.dc(['push'], docker_type='prod-build')
        self.dc(['push'], docker_type='prod-build', docker_vars={'BUILD_NUMBER': 'latest'})

    def deployment_cp(self, input, dest='~'):
        """Copies a file to the deployment"""
        command = ['scp', '-o', 'StrictHostKeyChecking=no']
        command += input
        command += [self.deployment_target + ":{}".format(dest)]
        call_subprocess(command, debug=self.debug)

    def deployment_exec(self, input):
        """Runs a command on the deployment"""
        target = self.deployment_target
        command = ['ssh', '-o', 'StrictHostKeyChecking=no', target]
        command += input
        call_subprocess(command, debug=self.debug)

    def deployment_ssh(self):
        """Opens an ssh connection to the deployment"""
        call_subprocess(['ssh', self.deployment_target], debug=self.debug)

    def predeploy(self):
        for config in self.predeploy_config:
            self.dc_run(
                input=config['command'].split(' '),
                service=config['service'], docker_type='prod-build'
            )

    def deploy(self, env_file=None):
        """Deploys docker images/static assets and starts services

        Parameters:
            env_file (str): name of env file to copy to production
        """
        self.predeploy()
        self.push()
        self.deployment_cp([env_file or '.env'], dest='~/.env')
        self.deployment_cp(['docker-compose.prod.yml'])
        self.deployment_exec(['docker', 'system',  'prune', '-a', '--force'])

        remote_docker_command = self.docker_vars_command + [
            'BUILD_NUMBER=latest', 'docker-compose',
            '-f', 'docker-compose.prod.yml'
        ]

        self.deployment_exec(remote_docker_command + ['pull'])
        self.deployment_exec(remote_docker_command + ['up', '-d'])

    def run_alias(self, alias, input=[], docker_type=None):
        alias_config = self.aliases.get(alias)
        command = alias_config['command'].split(' ') + input
        service = alias_config['service']
        if docker_type:
            self.dc_run(
                input=command, service=service, docker_type=docker_type
            )
        else:
            self.dc_run(input=command, service=service)
