from . import __version__
from .call_subprocess import (
    call_subprocess, NonZeroReturnCodeException,
    SubprocessExceptionHandler
)
from .call_docker_compose import call_docker_compose


class CommandException(Exception):
    pass


class Sykle():
    """Class for programatically invoking Sykle."""

    version = __version__

    def __init__(self, config, debug=False):
        self.config = config
        self.debug = debug

    def _run_commands(self, commands, exec=False, input=[], **kwargs):
        modified_kwargs = {**kwargs}
        docker_type = modified_kwargs.pop('docker_type', None)

        env = modified_kwargs.get('env', {})
        deployment = modified_kwargs.get('deployment')
        if deployment:
            env['DEPLOYMENT'] = deployment

        exception_handler = SubprocessExceptionHandler()

        for command in commands:
            command.input += input
            try:
                if command.service:
                    # FIXME: change "exec" to "use_exec" so we don't override exec keyword
                    if exec or command.use_exec:
                        self.dc_exec(
                            input=command.input,
                            service=command.service,
                            docker_type=docker_type or command.docker_type,
                            **modified_kwargs
                        )
                    else:
                        self.dc_run(
                            input=command.input,
                            service=command.service,
                            docker_type=docker_type or command.docker_type,
                            **modified_kwargs
                        )
                else:
                    self.call_subprocess(command.input, env=env)
            except NonZeroReturnCodeException as e:
                exception_handler.push(e)

        if self.debug:
            exception_handler.exit_with_stacktraces()
        else:
            exception_handler.exit_without_stacktraces()

    def _run_tests(self, commands, input=[], service=None, fast=False):
        commands = commands.for_service(service) if service else commands
        self._run_commands(
            commands, docker_type='test', exec=fast, input=input
        )

    def call_docker_compose(self, *args, **kwargs):
        return call_docker_compose(*args, **kwargs)

    def call_subprocess(self, *args, **kwargs):
        call_subprocess(*args, **kwargs, debug=self.debug)

    def dc(self, input, docker_type='dev', deployment=None, local_test=False):
        """
        Runs a command with the correct docker compose file(s)

        - local_test: if this is true, will ignore any deployment targets
        """

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
                if not local_test:
                    extras['target'] = deploy_config.target
                else:
                    extras['env_file'] = deploy_config.env_file
            else:
                extras['env_file'] = deploy_config.env_file

        project_name = self.config.get_project_name(docker_type=docker_type)
        self.call_docker_compose(
            input,
            project_name=project_name,
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

    def build(self, input=[], docker_type='dev', **kwargs):
        """Builds docker images based on compose files"""

        if docker_type == 'prod':
            self.dc(
                input=['build'] + input,
                docker_type='prod-build',
                **kwargs
            )
        else:
            # NB: all images that get deployed, or that we want to use to test
            #     deployments locally, should be prod. That means all dev
            #     and test images should forcefully ignore the deployment arg
            kwargs.pop('deployment', None)
            self.dc(input=['build'] + input, docker_type=docker_type, **kwargs)

    def up(self, input=[], **kwargs):
        """Starts up relevant docker compose services"""
        if kwargs.get('deployment'):
            kwargs['docker_type'] = 'prod'
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

    def preunittest(self):
        self._run_commands(
            self.config.preunittest_commands,
            docker_type='test'
        )

    def unittest(self, input=[], service=None, fast=False):
        if not fast:
            self.build(docker_type='test')

        self.preunittest()
        self._run_tests(self.config.unittest_commands, input, service, fast)

        if not fast:
            self.down(docker_type='test')

    def e2e(self, input=[], service=None, fast=False):
        if not fast:
            self.build(docker_type='test')

        self._run_tests(self.config.e2e_commands, input, service, fast)

        if not fast:
            self.down(docker_type='test')

    def push(self, deployment):
        """Pushes docker images"""
        self.dc(
            input=['push'],
            docker_type='prod-build',
            deployment=deployment
        )

    def pull(self, deployment=None):
        """Pulls docker images for a deployment (labels as prod images)"""
        self.dc(
            input=['pull'],
            docker_type='prod',
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

        self.pull(deployment=deployment)
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

    def run_alias(self, alias, input=[], **kwargs):
        self._run_commands(
            [self.config.get_alias_command(alias, input=input)],
            **kwargs
        )
