#!/usr/bin/python

"""Sykle CLI

Usage:
  syk dc [--debug] [--config=<file>] [--test | --prod | --prod-build] [INPUT ...]
  syk dc_run [--debug] [--config=<file>] [--service=<service>] [--test | --prod | --prod-build] [INPUT ...]
  syk dc_exec [--debug] [--config=<file>] [--service=<service>] [INPUT ...]
  syk build [--debug] [--config=<file>] [--test | --prod]
  syk up [--debug] [--config=<file>] [--test | --prod]
  syk down [--debug] [--config=<file>] [--test | --prod]
  syk unittest [--service=<service>] [--debug] [--config=<file>] [INPUT ...]
  syk e2e [--service=<service>] [--debug] [--config=<file>] [INPUT ...]
  syk push [--debug] [--config=<file>]
  syk ssh [--debug] [--config=<file>]
  syk ssh_cp [--debug] [--config=<file>] [--dest=<dest>] [INPUT ...]
  syk ssh_exec [--debug] [--config=<file>] [INPUT ...]
  syk deploy [--debug] [--config=<file>] [--env=<env_file>]
  syk [--debug] [--config=<file>] [INPUT ...]

Options:
  -h --help           Show help info
  --version           Show version
  --test              Run command with test compose file
  --prod              Run command with prod compose file
  --prod-build        Run command with prod-build compose file
  --config=<file>     Specify JSON config file [default: .sykle.json]
  --dest=<dest>       Destination path [default: ~]
  --env=<env_file>    Env file to use [default: .env]
  --service=<service> Docker service on which to run the command
  --debug             Prints debug information

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

.sykle.json:
  project_name        name of the project (used for naming docker images)
  default_service     default service to use when invoking dc_run
  deployment_target   ssh target address for deployment
  unittest            defines how to run unittests on services
  e2e                 defines how to run end-to-end tests on services
  docker_vars*        (optional) docker/docker-compose variables
"""
from .sykle import Sykle
from . import __version__
from docopt import docopt
import json


def main():
    args = docopt(__doc__, version=__version__)

    config = None
    with open(args['--config']) as f:
        config = json.load(f)

    input = args['INPUT']
    aliases = config.get('aliases', {})
    service = args['--service'] or config['default_service']

    docker_type = 'dev'
    if args['--test']:
        docker_type = 'test'
    elif args['--prod-build']:
        docker_type = 'prod-build'
    elif args['--prod']:
        docker_type = 'prod'

    sykle = Sykle(
        project_name=config['project_name'],
        deployment_target=config['deployment_target'],
        unittest_config=config.get('unittest', []),
        e2e_config=config.get('e2e', []),
        predeploy_config=config.get('predeploy', []),
        docker_vars=config.get('docker_vars', {}),
        aliases=aliases,
        debug=args['--debug']
    )

    if args['dc']:
        sykle.dc(input=input, docker_type=docker_type)
    elif args['dc_run']:
        sykle.dc_run(input=input, docker_type=docker_type, service=service)
    elif args['dc_exec']:
        sykle.dc_exec(input=input, docker_type=docker_type, service=service)
    elif args['build']:
        sykle.build(docker_type=docker_type)
    elif args['up']:
        sykle.up(docker_type=docker_type)
    elif args['down']:
        sykle.down(docker_type=docker_type)
    elif args['unittest']:
        sykle.unittest(input=input, service=service)
    elif args['e2e']:
        sykle.e2e(input=input, service=service)
    elif args['push']:
        sykle.push()
    elif args['ssh_cp']:
        sykle.deployment_cp(input=input, dest=args['--dest'])
    elif args['ssh_exec']:
        sykle.deployment_exec(input=input)
    elif args['ssh']:
        sykle.deployment_ssh()
    elif args['deploy']:
        sykle.deploy(env_file=args['--env'])
    else:
        try:
            alias = input[0] if len(input) > 0 else None
            input = input[1:] if len(input) > 1 else []
            if aliases.get(alias):
                sykle.run_alias(alias=alias, input=input)
            else:
                print('Unknown alias "{}"'.format(alias))
                print(__doc__)
        except Exception as e:
            print(e)
            pass
