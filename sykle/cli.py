#!/usr/bin/python3

# flake8: noqa
"""Sykle CLI
Usage:
  syk [--debug] [--config=<file>] [--test | --prod | --prod-build] [--local-test] dc [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod | --prod-build] [--service=<service>] [--env=<env_file>] [--deployment=<name>] [--local-test] dc_run [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod] [--service=<service>] dc_exec [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod] [--deployment=<name>] [--local-test] build [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod] [--deployment=<name>] [--local-test] up [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod] [--deployment=<name>] [--local-test] down
  syk [--debug] [--config=<file>] [--service=<service>] [--fast] unittest [INPUT ...]
  syk [--debug] [--config=<file>] [--service=<service>] [--fast] e2e [INPUT ...]
  syk [--debug] [--config=<file>] [--deployment=<name>] push
  syk [--debug] [--config=<file>] [--deployment=<name>] ssh
  syk [--debug] [--config=<file>] [--deployment=<name>] [--dest=<dest>] ssh_cp [INPUT ...]
  syk [--debug] [--config=<file>] [--deployment=<name>] ssh_exec [INPUT ...]
  syk [--debug] [--config=<file>] [--env=<env_file>] [--deployment=<name>] deploy
  syk init
  syk plugins
  syk plugins install
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
  --local-test            Use this in conjunction with the deployment argument
                          if you want to use all the settings for a specific
                          deployment, but have the command run locally rather
                          than on that deployment

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
  plugins install Installs plugin requirements
  config          Print an example config
"""

from . import __version__

import os
import sys
import time
import logging

from docopt import docopt

from .plugin_utils import Plugins
from .config import Config
from .sykle import Sykle, CommandException
from .call_subprocess import call_subprocess, CancelException, NonZeroReturnCodeException
from .logger import FancyLogger

logging.setLoggerClass(FancyLogger)
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def _load_config(args):
    config_name = args['--config'] or Config.FILENAME
    try:
        return Config.from_file(config_name)
    except Config.ConfigFileNotFoundException:
        message = """Config file %s does not exist!
            You can create an empty config by running:
            \tsyk init""" % config_name
        logger.critical(message)
    except Config.ConfigFileDecodeException as e:
        logger.critical('Config Decode Error: %s' % e)


def _get_docker_type(args):
    if args['--test']:
        return 'test'
    elif args['--prod-build']:
        return 'prod-build'
    elif args['--prod']:
        return 'prod'
    return 'dev'


def use_run_file():
    logger.warn(
        """========================UPGRADE===========================
                         Legacy run.sh detected!
          Will try to run commands through ./run.sh until removed
        =========================================================="""
    )
    time.sleep(1)

    logger.warn('Trying to run command with run.sh...')
    # NB: always run debug when trying to use legacy ./run.sh file
    p = call_subprocess(['./run.sh'] + sys.argv[1:], debug=True)
    if p.returncode == 1:
        logger.info('command failed through run.sh. Trying to run normally...')
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
        plugins = Plugins.list()
        if args['install']:
            logger.info('Installing plugins:')
            for plugin_name, plugin_dir in plugins.items():
                logger.info('  {}'.format(plugin_name))
                plugin_dir.install_requirements()
            return
        logger.info('Available plugins:')
        for plugin_name in plugins.keys():
            logger.info('  {}'.format(plugin_name))
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
        local_test = args['--local-test']
        sykle.dc(
            input=args['INPUT'], docker_type=docker_type,
            local_test=local_test
        )
    elif args['dc_run']:
        local_test = args['--local-test']
        service = args['--service'] or config.default_service
        deployment = args['--deployment']
        sykle.dc_run(
            input=args['INPUT'], docker_type=docker_type,
            service=service, deployment=deployment,
            local_test=local_test
        )
    elif args['dc_exec']:
        service = args['--service'] or config.default_service
        sykle.dc_exec(
            input=args['INPUT'], docker_type=docker_type,
            service=service
        )
    elif args['build']:
        local_test = args['--local-test']
        deployment = args['--deployment']
        if deployment:
            # NB: all images that get deployed, or that we want to use to test
            #     deployments locally, should be prod.
            docker_type = 'prod'
        sykle.build(
            docker_type=docker_type, deployment=deployment,
            local_test=local_test, input=args['INPUT']
        )
    elif args['up']:
        local_test = args['--local-test']
        deployment = args['--deployment']
        sykle.up(
            docker_type=docker_type, deployment=deployment,
            input=args['INPUT'], local_test=local_test
        )
    elif args['down']:
        local_test = args['--local-test']
        deployment = args['--deployment']
        sykle.down(
            docker_type=docker_type, deployment=deployment,
            local_test=local_test
        )
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
            logger.critical('Unknown alias/plugin "{}"'.format(cmd))
            print(__doc__)

def main():
    args = docopt(__doc__, version=__version__, options_first=True)

    try:
        process_args(args)
    except CancelException:
        logger.critical('Canceled')
    except CommandException as e:
        logger.critical(e)
    except Config.ConfigException as e:
        logger.critical(e)
    except NonZeroReturnCodeException as e:
        logger.critical(e)
