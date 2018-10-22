#!/usr/bin/python

"""Sykle CLI
Usage:
  syk [--debug] [--config=<file>] [--test | --prod | --prod-build] dc [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod | --prod-build] [--service=<service>] [--env=<env_file>] dc_run [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod] [--service=<service>] dc_exec [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod] [--deployment=<name>] build
  syk [--debug] [--config=<file>] [--test | --prod] up
  syk [--debug] [--config=<file>] [--test | --prod] down
  syk [--debug] [--config=<file>] [--service=<service>] unittest [INPUT ...]
  syk [--debug] [--config=<file>] [--service=<service>] e2e [INPUT ...]
  syk [--debug] [--config=<file>] [--deployment=<name>] push
  syk [--debug] [--config=<file>] [--deployment=<name>] ssh
  syk [--debug] [--config=<file>] [--deployment=<name>] [--dest=<dest>] ssh_cp [INPUT ...]
  syk [--debug] [--config=<file>] [--deployment=<name>] ssh_exec [INPUT ...]
  syk [--debug] [--config=<file>] [--env=<env_file>] [--deployment=<name>] deploy
  syk init
  syk plugins
  syk config
  syk [--debug] [--config=<file>] [INPUT ...]

Option
  -h --help               Show help info
  --version               Show version
  --test                  Run command with test compose file
  --prod                  Run command with prod compose file
  --prod-build            Run command with prod-build compose file
  --config=<file>         Specify JSON config file
  --dest=<dest>           Destination path [default: ~]
  --env=<env_file>        Env file to use [default: .env]
  --service=<service>     Docker service on which to run the command
  --debug                 Prints debug information
  --deployment=<name>     Uses config for the given deployment

Description:
  dc              Runs docker-compose command
  dc_run          Spins up and runs a command on a docker-compose service
  dc_exec         Runs a command on an existing docker-compose container
  build           Builds docker-compose images
  up              Starts docker-compose
  down            Stops docker-compose
  unittest        Runs unittests on all services defined in "unittest"
  e2e             Runs end to end tests on all services defined in "e2e"
  push            Pushes images using "docker-compose.prod-build.yml"
  ssh             Connects to the ssh target
  ssh_cp          Copies file to ssh target home directory
  ssh_exec        Executes command on ssh target
  deploy          Deploys and starts latest builds on ssh target
  init            Creates a blank config file
  plugins         Lists available plugins
  config          Print an example config
"""
from .sykle import Sykle
from .plugins import Plugins
from .config import Config
from . import __version__
from docopt import docopt
import os

config_example_PATH = os.path.join(
    os.path.dirname(__file__),
    '.sykle.example.json'
)


def _load_config(args):
    config_name = args['--config'] or Config.FILENAME
    try:
        return Config.from_file(config_name)
    except Config.ConfigFileNotFoundError:
        print(
            '\033[91m' +
            "Config file '{}' does not exist!\n".format(config_name) +
            "You can create an empty config by running: \n" +
            "    syk init" +
            '\033[0m'
        )
        return
    except Config.ConfigFileDecodeError as e:
        print(
            '\033[91m' +
            'Config Decode Error: {}'.format(e) +
            '\033[0m'
        )
        return


def _get_docker_type(args):
    if args['--test']:
        return 'test'
    elif args['--prod-build']:
        return 'prod-build'
    elif args['--prod']:
        return 'prod'
    return 'dev'


def _load_docker_vars_for_deployment(config, deployment):
    return Config.interpolate_env_values(
        config.for_deployment(deployment).get('docker_vars', {}),
        os.environ
    )


def main():
    args = docopt(__doc__, version=__version__, options_first=True)

    # --- Run commands that do not require sykle instance ---

    if args['init']:
        Config.init(enable_print=True)
        return
    elif args['config']:
        print(Config.CONFIG_FILE_EXAMPLE)
        return

    # --- Load config and docker type ---

    docker_type = _get_docker_type(args)
    config = _load_config(args)
    if not config:
        return

    # --- Set up argument defaults based on config ---

    service = args['--service'] or config.default_service
    deployment = args['--deployment'] or config.default_deployment

    # --- Create sykle instance ---

    sykle = Sykle(
        project_name=config.project_name,
        unittest_config=config.unittest,
        e2e_config=config.e2e,
        predeploy_config=config.predeploy,
        aliases=config.aliases,
        debug=args['--debug']
    )

    # --- Run commands that require sykle instance ---

    if args['dc']:
        sykle.dc(input=args['INPUT'], docker_type=docker_type)
    elif args['dc_run']:
        sykle.dc_run(input=args['INPUT'], docker_type=docker_type, service=service)
    elif args['dc_exec']:
        sykle.dc_exec(input=args['INPUT'], docker_type=docker_type, service=service)
    elif args['build']:
        docker_vars = {}
        if docker_type == 'prod':
            docker_vars = _load_docker_vars_for_deployment(config, deployment)
        elif args['--deployment']:
            print(
                '\033[93m' +
                'No --prod flag found, ignoring --deployment option' +
                '\033[0m'
                .format(Config.FILENAME)
            )
        sykle.build(docker_type=docker_type, docker_vars=docker_vars)
    elif args['up']:
        sykle.up(docker_type=docker_type)
    elif args['down']:
        sykle.down(docker_type=docker_type)
    elif args['unittest']:
        sykle.unittest(input=args['INPUT'], service=service)
    elif args['e2e']:
        sykle.e2e(input=args['INPUT'], service=service)
    elif args['push']:
        docker_vars = _load_docker_vars_for_deployment(config, deployment)
        sykle.push(docker_vars=docker_vars)
    elif args['ssh_cp']:
        deployment_config = config.for_deployment(deployment)
        sykle.deployment_cp(
            input=args['INPUT'], dest=args['--dest'],
            target=deployment_config['target']
        )
    elif args['ssh_exec']:
        deployment_config = config.for_deployment(deployment)
        sykle.deployment_exec(input=args['INPUT'], target=deployment_config['target'])
    elif args['ssh']:
        deployment_config = config.for_deployment(deployment)
        sykle.deployment_ssh(target=deployment_config['target'])
    elif args['deploy']:
        deployment_config = config.for_deployment(deployment)
        docker_vars = deployment_config.get('docker_vars', {})
        env_file = deployment_config.get('env_file', args['--env'])
        target = deployment_config['target']
        sykle.deploy(target=target, env_file=env_file, docker_vars=docker_vars)
    elif args['plugins']:
        print('Installed syk plugins:')
        plugins = Plugins(config=config)
        for plugin in plugins.list():
            print('  {}'.format(plugin))
    else:
        cmd = input[0] if len(args['INPUT']) > 0 else None
        input = input[1:] if len(args['INPUT']) > 1 else []
        plugins = Plugins(config=config)
        if config.aliases.get(cmd):
            sykle.run_alias(alias=cmd, input=input)
        elif plugins.exists(cmd):
            plugins.run(cmd)
        else:
            print('Unknown alias/plugin "{}"'.format(cmd))
            print(__doc__)
