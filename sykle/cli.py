#!/usr/bin/python

# flake8: noqa
"""Sykle CLI
Usage:
  syk [--debug] [--config=<file>] [--test | --prod | --prod-build] dc [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod | --prod-build] [--service=<service>] [--env=<env_file>] [--deployment=<name>] dc_run [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod] [--service=<service>] dc_exec [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod] [--deployment=<name>] build
  syk [--debug] [--config=<file>] [--test | --prod] [--deployment=<name>] up
  syk [--debug] [--config=<file>] [--test | --prod] [--deployment=<name>] down
  syk [--debug] [--config=<file>] [--service=<service>] [--fast] unittest [INPUT ...]
  syk [--debug] [--config=<file>] [--service=<service>] [--fast] e2e [INPUT ...]
  syk [--debug] [--config=<file>] [--deployment=<name>] push
  syk [--debug] [--config=<file>] [--deployment=<name>] ssh
  syk [--debug] [--config=<file>] [--deployment=<name>] [--dest=<dest>] ssh_cp [INPUT ...]
  syk [--debug] [--config=<file>] [--deployment=<name>] ssh_exec [INPUT ...]
  syk [--debug] [--config=<file>] [--env=<env_file>] [--deployment=<name>] deploy
  syk init
  syk plugins
  syk config
  syk [--debug] [--config=<file>] [--deployment=<name>] [INPUT ...]

Option
  -h --help               Show help info
  --version               Show version
  --test                  Run command with test compose file
  --prod                  Run command with prod compose file
  --prod-build            Run command with prod-build compose file
  --config=<file>         Specify JSON config file
  --dest=<dest>           Destination path [default: ~]
  --env=<env_file>        Env file to use
  --service=<service>     Docker service on which to run the command
  --debug                 Prints debug information
  --deployment=<name>     Uses config for the given deployment
  --fast                  Runs tests without building images/containers
                          (you will need to have 'syk --test up' running)

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

from . import __version__
from .plugin_utils import Plugins
from .config import Config
from .sykle import Sykle, CommandException
from .call_subprocess import call_subprocess, CancelException, NonZeroReturnCodeException
from docopt import docopt
import os
import sys
import time

CEND = '\33[0m'
CYELLOW = '\33[33m'
CRED = '\33[31m'

def _load_config(args):
    config_name = args['--config'] or Config.FILENAME
    try:
        return Config.from_file(config_name)
    except Config.ConfigFileNotFoundException:
        print(
            CRED +
            "Config file '{}' does not exist!\n".format(config_name) +
            "You can create an empty config by running: \n" +
            "    syk init" +
            CEND
        )
        return
    except Config.ConfigFileDecodeException as e:
        print(
            CRED +
            'Config Decode Error: {}'.format(e) +
            CEND
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


def use_run_file():
    print(CYELLOW)
    print('========================UPGRADE===========================')
    print('                 Legacy run.sh detected!                  ')
    print('  Will try to run commands through ./run.sh until removed ')
    print('==========================================================')
    print(CEND)
    time.sleep(1)

    print('Trying to run command with run.sh...')
    # NB: always run debug when trying to use legacy ./run.sh file
    p = call_subprocess(['./run.sh'] + sys.argv[1:], debug=True)
    if p.returncode == 1:
        print(CRED)
        print('command failed through run.sh. Trying to run normally...')
        print(CEND)
    else:
        return

def process_args(args):
    # --- Run commands that do not require sykle instance ---

    # NB: should remove this if there are no more Type/Code projects using
    #     ./run.sh files
    if os.path.isfile('run.sh'):
        use_run_file()

    if args['init']:
        Config.init(enable_print=True)
        return
    elif args['plugins']:
        print('Installed syk plugins:')
        for plugin in Plugins.list():
            print('  {}'.format(plugin))
        return
    elif args['config']:
        Config.print_example()
        return

    # --- Load config and docker type ---

    docker_type = _get_docker_type(args)
    config = _load_config(args)
    if not config:
        return

    # --- Create sykle instance ---

    sykle = Sykle(config, debug=args['--debug'])

    # --- Run commands that require sykle instance ---

    if args['dc']:
        sykle.dc(
            input=args['INPUT'], docker_type=docker_type
        )
    elif args['dc_run']:
        service = args['--service'] or config.default_service
        deployment = args['--deployment']
        sykle.dc_run(
            input=args['INPUT'], docker_type=docker_type,
            service=service, deployment=deployment
        )
    elif args['dc_exec']:
        service = args['--service'] or config.default_service
        sykle.dc_exec(
            input=args['INPUT'], docker_type=docker_type,
            service=service
        )
    elif args['build']:
        deployment = args['--deployment'] or config.default_deployment
        sykle.build(docker_type=docker_type, deployment=deployment)
    elif args['up']:
        deployment = args['--deployment']
        sykle.up(docker_type=docker_type, deployment=deployment)
    elif args['down']:
        deployment = args['--deployment']
        sykle.down(docker_type=docker_type, deployment=deployment)
    elif args['unittest']:
        sykle.unittest(
            input=args['INPUT'], service=args['--service'],
            fast=args['--fast']
        )
    elif args['e2e']:
        sykle.e2e(
            input=args['INPUT'], service=args['--service'],
            fast=args['--fast']
        )
    elif args['push']:
        deployment = args['--deployment'] or config.default_deployment
        sykle.push(deployment=deployment)
    elif args['ssh_cp']:
        deployment = args['--deployment'] or config.default_deployment
        sykle.ssh_cp(
            input=args['INPUT'], deployment=deployment,
            dest=args['--dest'],
        )
    elif args['ssh_exec']:
        deployment = args['--deployment'] or config.default_deployment
        sykle.ssh_exec(
            input=args['INPUT'],
            deployment=deployment
        )
    elif args['ssh']:
        deployment = args['--deployment'] or config.default_deployment
        sykle.ssh(deployment=deployment)
    elif args['deploy']:
        deployment = args['--deployment'] or config.default_deployment
        sykle.deploy(deployment)
    else:
        deployment = args['--deployment']
        input = args['INPUT']
        cmd = input[0] if len(input) > 0 else None
        input = input[1:] if len(input) > 1 else []
        plugins = Plugins(config=config, sykle=sykle)
        if config.has_alias(cmd):
            sykle.run_alias(alias=cmd, input=input, deployment=deployment)
        elif plugins.exists(cmd):
            plugins.run(cmd)
        else:
            print('Unknown alias/plugin "{}"'.format(cmd))
            print(__doc__)

def main():
    args = docopt(__doc__, version=__version__, options_first=True)

    try:
        process_args(args)
    except CancelException:
        print(CRED + '\nCancelled' + CEND)
    except CommandException as e:
        print(CRED + '\n{}'.format(e) + CEND)
    except Config.ConfigException as e:
        print(CRED + '\n{}'.format(e) + CEND)
    except NonZeroReturnCodeException as e:
        print(CRED + '\n{}'.format(e) + CEND)
