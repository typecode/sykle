from .call_subprocess import call_subprocess, NonZeroReturnCodeException


class CommandException(Exception):
    pass


class Sykle():
    version = '0.5.1'
    """
    Class for programatically invoking Sykle
    """
    def __init__(self, config, debug=False):
        self.config = config
        self.debug = debug

    def _run_commands(self, commands, exec=False, **kwargs):
        for command in commands:
            try:
                if command.service:
                    if exec:
                        self.dc_exec(
                            input=command.input,
                            service=command.service,
                            **kwargs
                        )
                    else:
                        self.dc_run(
                            input=command.input,
                            service=command.service,
                            **kwargs
                        )
                else:
                    self.call_subprocess(command.input)
            except NonZeroReturnCodeException:
                raise CommandException("Command {} failed".format(command))

    def _run_tests(self, commands, input=[], service=None, fast=False):
        if not fast:
            self.build(docker_type='test')

        commands = commands.for_service(service) if service else commands

        self._run_commands(commands, docker_type='test', exec=fast)

        if not fast:
            self.down(docker_type='test')

    def call_subprocess(self, *args, **kwargs):
        call_subprocess(*args, **kwargs, debug=self.debug)

    def dc(self, input, docker_type='dev', deployment=None):
        """Runs a command with the correct docker compose file(s)"""
        from .call_docker_compose import call_docker_compose

        extras = {'type': docker_type}

        if deployment:
            print(
                'Using `prod` docker type and {} docker vars...'
                .format(deployment)
            )
            deploy_config = self.config.for_deployment(deployment)
            extras['docker_vars'] = deploy_config.docker_vars

            if docker_type != 'prod-build':
                extras['type'] = 'prod'
                extras['target'] = deploy_config.target
            else:
                extras['env_file'] = deploy_config.env_file

        call_docker_compose(
            input,
            project_name=self.config.get_project_name(docker_type),
            debug=self.debug, **extras
        )

    def dc_run(self, input, service, **kwargs):
        """
        Spins up and runs a command on a container representing a
        docker compose service
        """
        self.dc(input=['run', '--rm', service] + input, **kwargs)

    def dc_exec(self, input, service, **kwargs):
        """Runs a command on a running service container"""
        self.dc(input=['exec', service] + input, **kwargs)

    def build(self, docker_type='dev', deployment=None):
        """Builds docker images based on compose files"""

        if docker_type == 'prod':
            self.dc(
                input=['build'],
                docker_type='prod-build',
                deployment=deployment
            )
        else:
            self.dc(input=['build'], docker_type=docker_type)

    def up(self, input=[], **kwargs):
        """Starts up relevant docker compose services"""
        self.preup(**kwargs)
        self.dc(
            input=['up', '--build', '--force-recreate'] + input,
            **kwargs
        )

    def down(self, input=[], **kwargs):
        """Spins down relevant docker compose services"""
        self.dc(
            input=['down'] + input,
            **kwargs
        )

    def unittest(self, input=[], service=None, fast=False):
        self._run_tests(self.config.unittest_commands, input, service, fast)

    def e2e(self, input=[], service=None, fast=False):
        self._run_tests(self.config.e2e_commands, input, service, fast)

    def push(self, deployment):
        """Pushes docker images"""
        self.dc(
            input=['push'],
            docker_type='prod-build',
            deployment=deployment
        )

    def pull(self, deployment):
        """Pushes docker images"""
        self.dc(
            input=['pull'],
            deployment=deployment
        )

    def ssh_cp(self, input, deployment, dest='~'):
        """Copies a file to the deployment"""
        deploy_config = self.config.for_deployment(deployment)
        command = ['scp', '-o', 'StrictHostKeyChecking=no']
        command += input
        command += [deploy_config.target + ":{}".format(dest)]
        self.call_subprocess(command)

    def ssh_exec(self, input, deployment):
        deploy_config = self.config.for_deployment(deployment)
        self.call_subprocess(input, target=deploy_config.target)

    def ssh(self, deployment):
        """Opens an ssh connection to the deployment"""
        deploy_config = self.config.for_deployment(deployment)
        self.call_subprocess(['ssh', deploy_config.target])

    def deploy(self, deployment):
        """Deploys docker images/static assets and starts services"""
        deploy_config = self.config.for_deployment(deployment)

        self.predeploy(deployment)
        self.push(deployment)

        self.ssh_cp(
            input=[deploy_config.env_file],
            deployment=deployment, dest='~/.env'
        )
        self.ssh_cp(
            input=['docker-compose.prod.yml'],
            deployment=deployment
        )

        self.dc(input=['pull'], deployment=deployment)
        self.up(input=['-d'], deployment=deployment)

        # cleans up docker system
        # TODO: might want to make this optional
        self.ssh_exec(
            ['docker', 'system', 'prune', '-a', '--force'],
            deployment=deployment
        )

    def preup(self, **kwargs):
        self._run_commands(self.config.preup_commands, **kwargs)

    def predeploy(self, deployment):
        self._run_commands(
            self.config.predeploy_commands,
            docker_type='prod-build', deployment=deployment
        )

    def run_alias(self, alias, input=[], docker_type='dev', deployment=None):
        self._run_commands(
            [self.config.get_alias_command(alias, input=input)],
            docker_type=docker_type, deployment=deployment, exec=False
        )
