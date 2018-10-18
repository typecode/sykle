#!/usr/bin/python

"""Sykle CLI
NOTE:
  Options must be declared BEFORE the command (this allows us to create plugins)

Usage:
  syk [--debug] [--config=<file>] [--test | --prod | --prod-build] dc [INPUT ...]
  syk [--debug] [--config=<file>] [--service=<service>] [--test | --prod | --prod-build] dc_run [INPUT ...]
  syk [--debug] [--config=<file>] [--service=<service>] dc_exec [INPUT ...]
  syk [--debug] [--config=<file>] [--test | --prod] build
  syk [--debug] [--config=<file>] [--test | --prod] up
  syk [--debug] [--config=<file>] [--test | --prod] down
  syk [--service=<service>] [--debug] [--config=<file>] unittest [INPUT ...]
  syk [--service=<service>] [--debug] [--config=<file>] e2e [INPUT ...]
  syk [--debug] [--config=<file>] push
  syk [--debug] [--config=<file>] ssh
  syk [--debug] [--config=<file>] [--dest=<dest>] ssh_cp [INPUT ...]
  syk [--debug] [--config=<file>] ssh_exec [INPUT ...]
  syk [--debug] [--config=<file>] [--env=<env_file>] [--location=<location>] deploy
  syk init
  syk plugins
  syk [--debug] [--config=<file>] [INPUT ...]

Options:
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
  --location=<location>   Location to deploy to

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

.sykle.json:
  project_name        name of the project (used for naming docker images)
  default_service     default service to use when invoking dc_run
  deployment_target   ssh target address for deployment
  unittest            defines how to run unittests on services
  e2e                 defines how to run end-to-end tests on services
  docker_vars*        (optional) docker/docker-compose variables
  plugins*            (optional) hash containing plugin specific configuration
"""
from .sykle import Sykle
from .plugins import Plugins
from .config import Config
from . import __version__
from docopt import docopt


def main():
    args = docopt(__doc__, version=__version__, options_first=True)

    if args['init']:
        Sykle.init()
        return

    config = Config.from_file(args['--config'] or Config.FILENAME)
    input = args['INPUT']
    aliases = config.aliases
    service = args['--service'] or config.default_service
    plugins = Plugins(config=config)
    location = args['--location'] or config.default_deployment

    docker_type = 'dev'
    if args['--test']:
        docker_type = 'test'
    elif args['--prod-build']:
        docker_type = 'prod-build'
    elif args['--prod']:
        docker_type = 'prod'

    sykle = Sykle(
        project_name=config.project_name,
        unittest_config=config.unittest,
        e2e_config=config.e2e,
        predeploy_config=config.predeploy,
        docker_vars=config.docker_vars,
        aliases=config.aliases,
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
        # NB: we're not calling ".for_deployment" at the top of this file
        #     because we only want to get/validate deployment configs when
        #     we're using them
        deployment_config = config.for_deployment(location)
        sykle.deployment_cp(
            input=input, dest=args['--dest'],
            target=deployment_config['target']
        )
    elif args['ssh_exec']:
        deployment_config = config.for_deployment(location)
        sykle.deployment_exec(input=input, target=deployment_config['target'])
    elif args['ssh']:
        deployment_config = config.for_deployment(location)
        sykle.deployment_ssh(target=deployment_config['target'])
    elif args['deploy']:
        deployment_config = config.for_deployment(location)
        env_file = deployment_config.get('env_file', args['--env'])
        target = deployment_config['target']
        sykle.deploy(target=target, env_file=env_file)
    elif args['plugins']:
        print('Installed syk plugins:')
        for plugin in plugins.list():
            print('  {}'.format(plugin))
    else:
        cmd = input[0] if len(input) > 0 else None
        input = input[1:] if len(input) > 1 else []
        if aliases.get(cmd):
            sykle.run_alias(alias=cmd, input=input)
        elif plugins.exists(cmd):
            plugins.run(cmd)
        else:
            print('Unknown alias/plugin "{}"'.format(cmd))
            print(__doc__)
