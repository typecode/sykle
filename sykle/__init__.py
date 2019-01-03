# __init__.py

__version__ = '0.4.0'


class Sykle():
    """
    Class for programatically invoking Sykle
    """
    version = __version__

    def __init__(
        self, project_name='sykle-project',
        unittest_config=[], e2e_config=[],
        predeploy_config=[], debug=False,
        aliases={}
    ):
        """
        Parameters:
            debug (bool): Set to true to print debug information
            project_name (str): Name of the entire project
            unittest_config (array[dict]): Array of unittest configs
            e2e_config (array[dict]): Array of end to end test configs
            predeploy_config (array[dict]): Array with predeploy steps
            aliases (dict): Dictionary defining custom commands
        """
        from .call_subprocess import call_subprocess
        self.call_subprocess = call_subprocess
        self.aliases = aliases
        self.debug = debug
        self.project_name = project_name
        self.e2e_config = e2e_config
        self.predeploy_config = predeploy_config
        self.unittest_config = unittest_config

    def _read_env_file(self, env_file):
        import dotenv
        return dotenv.dotenv_values(env_file)

    def _run_tests(
        self, configs, warning=None, input=[],
        service=None, fast=False
    ):
        if not configs and warning:
            print(warning)
            return

        if not fast:
            self.build(docker_type='test')

        for config in configs:
            if service and (config['service'] != service):
                continue
            command = config['command'].split(' ') + input
            service = config['service']
            if fast:
                self.dc_exec(command, service=service, docker_type='test')
            else:
                self.dc_run(command, service=service, docker_type='test')

    def _add_latest_build_tag(self, docker_vars):
        # TODO: This assumes the docker compose file has
        #       a BUILD_NUMBER env var used to tag images.
        #       There should be a better way to tag builds that
        #       doesn't make that assumption
        _docker_vars = docker_vars.copy()
        _docker_vars['BUILD_NUMBER'] = 'latest'
        return _docker_vars

    def _remote_docker_compose_command(self, docker_vars):
        """Supplies env args and defines beginning of remote command"""
        _docker_vars = self._add_latest_build_tag(docker_vars)
        return ["{}={}".format(k, v) for k, v in _docker_vars.items()] + [
            'docker-compose', '-f', 'docker-compose.prod.yml'
        ]

    def dc(self, input, docker_type='dev', docker_vars={}, target=None):
        """Runs a command with the correct docker compose file(s)"""
        from .dc_runner import DCRunner
        DCRunner(
            type=docker_type,
            project_name=self.project_name,
            debug=self.debug,
            docker_vars=docker_vars,
            target=target
        ).call(input)

    def dc_run(
        self, input, service, docker_type='dev',
        env_file=None, docker_vars={}, target=None
    ):
        """
        Spins up and runs a command on a container representing a
        docker compose service
        """
        opts = []
        if env_file:
            # NB: as of this comment, docker-compose does not have an
            #     --env-file option. If it did, we would use it here.
            #     See: https://github.com/docker/compose/issues/6170
            env = self._read_env_file(env_file)
            env_opts = [["-e", "{}={}".format(k, v)] for k, v in env.items()]
            opts = opts + [a for b in env_opts for a in b]
        opts += ['--rm']
        self.dc(
            input=['run'] + opts + [service] + input,
            docker_type=docker_type,
            docker_vars=docker_vars,
            target=target
        )

    def dc_exec(self, input, service=None, docker_type='dev', docker_vars={}):
        """Runs a command on a running service container"""
        self.dc(
            input=['exec', service] + input,
            docker_type=docker_type,
            docker_vars=docker_vars
        )

    def build(self, docker_type='dev', docker_vars={}):
        """Builds docker images based on compose files"""
        if docker_type == 'prod':
            self.dc(
                input=['build'],
                docker_type='prod-build',
                docker_vars=docker_vars,
            )
            self.dc(
                input=['build'],
                docker_type='prod-build',
                docker_vars=self._add_latest_build_tag(docker_vars)
            )
        else:
            self.dc(
                input=['build'],
                docker_type=docker_type
            )

    def up(self, docker_type='dev'):
        """Starts up relevant docker compose services"""
        self.dc(
            input=['up', '--build', '--force-recreate'],
            docker_type=docker_type
        )

    def down(self, docker_type='dev'):
        """Spins down relevant docker compose services"""
        self.dc(
            input=['down'],
            docker_type=docker_type
        )

    def unittest(self, input=[], service=None, fast=False):
        self._run_tests(
            self.unittest_config,
            warning='No unittests configured!',
            input=input, service=service,
            fast=fast
        )

    def e2e(self, input=[], service=None, fast=False):
        self._run_tests(
            self.e2e_config,
            warning='No end to end tests configured!',
            input=input, service=service,
            fast=fast
        )

    def push(self, docker_vars={}):
        """Pushes docker images"""
        self.dc(['push'], docker_type='prod-build', docker_vars=docker_vars)
        self.dc(
            ['push'],
            docker_type='prod-build',
            docker_vars=self._add_latest_build_tag(docker_vars)
        )

    def deployment_cp(self, input, target, dest='~'):
        """Copies a file to the deployment"""
        command = ['scp', '-o', 'StrictHostKeyChecking=no']
        command += input
        command += [target + ":{}".format(dest)]
        return self.call_subprocess(command, debug=self.debug)

    def deployment_exec(self, input, target):
        """Runs a command on the deployment"""
        command = ['ssh', '-o', 'StrictHostKeyChecking=no', target]
        command += input
        return self.call_subprocess(command, debug=self.debug)

    def deployment_ssh(self, target):
        """Opens an ssh connection to the deployment"""
        return self.call_subprocess(['ssh', target], debug=self.debug)

    def predeploy(self, env_file=None, docker_vars={}):
        for config in self.predeploy_config:
            self.dc_run(
                input=config['command'].split(' '),
                service=config['service'],
                docker_type='prod-build',
                env_file=env_file,
                docker_vars=docker_vars
            )

    def deploy(self, target, env_file=None, docker_vars={}):
        """Deploys docker images/static assets and starts services"""
        self.predeploy(env_file=env_file, docker_vars=docker_vars)
        self.push(docker_vars=docker_vars)
        self.deployment_cp([env_file], target=target, dest='~/.env')
        self.deployment_cp(['docker-compose.prod.yml'], target=target)
        # TODO: might want to make this optional
        self.deployment_exec(
            ['docker', 'system', 'prune', '-a', '--force'], target=target
        )

        command = self._remote_docker_compose_command(docker_vars)
        self.deployment_exec(command + ['pull'], target=target)
        self.deployment_exec(command + ['up', '-d'], target=target)

    def run_alias(self, alias, input=[], docker_type=None, docker_vars={}, target=None):
        alias_config = self.aliases.get(alias)
        is_exec = alias_config.get('exec', False)
        command = alias_config['command'].split(' ') + input
        service = alias_config['service']
        kwargs = {'docker_vars': docker_vars, 'input': command, 'service': service, 'target': target}

        if is_exec:
            self.dc_exec(**kwargs)
        elif docker_type:
            self.dc_run(docker_type=docker_type, **kwargs)
        else:
            self.dc_run(**kwargs)
