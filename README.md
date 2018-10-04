# sykle

Sykle is a cli tool for calling commonly used commands in docker-compose projects.

#### What sykle does

- Enforces 3 docker-compose environments: `dev`, `test`, and `prod`
- Provides commands for spinning up dev, running tests, and deploying to prod
  - (Assumes you are deploying to a single remote instance running docker-compose)
- Allows you to write aliases for commonly used commands that run on specific docker-compose services
- Provides additional commonly used devops commands (which may or may not run through docker-compose) via plugins

#### What sykle does not do

- Does not spin up remote instances (may add Terraform in the future to do this)
- Does not generate DockerFiles, Docker-Compsoe files, etc
- Does not replace standard devops tools
  - (plugins should delegate to other tools)

### Requirements

- `docker` (locally and on deployment target)
- `docker-compose` (locally and on deployment target)
- `ssh`
- `scp`

### Installation

`pip install git+ssh://git@github.com/typecode/sykle.git`

### Configuration

Because sykle tries to make as few assumptions about your project as possible, you'll need to declaritively define how your app should run via static configuration files

#### Docker Compose

Sykle uses 4 different docker-compose configurations:

- `docker-compose.yml` for development
- `docker-compose.test.yml` for testing
- `docker-compose.prod-build.yml` for building/deploying production
- `docker-compose.prod.yml` for running production

These separate configurations allow you to tweak how your projects run in those 4 standard scenarios, and helps ensure that there no conflicting assumptions between environments.

#### .sykle.json

In addition to your `docker-compose` files, you'll need a `.sykle.json`. See below for a sample.

*Example:*
```json
{
    "version": 1,
    "project_name": "cool-project",
    "default_service": "django",
    "default_deployment": "staging",
    "unittest": [
        {
            "service": "django",
            "command": "django-admin test"
        },
        {
            "service": "node",
            "command": "npm test"
        }
    ],
    "e2e": [
        {
            "service": "django",
            "command": "behave"
        }
    ],
    "predeploy": [
        {
            "service": "django",
            "command": "django-admin collectstatic --no-input"
        }
    ],
    "deployments": {
        "prod": {
            "target": "ec2-user@www.my-site.com",
            "env_file": ".env.prod",
        },
        "staging": {
            "target": "ect-user@staging.my-site.com",
            "env_file": ".env.staging",
        }
    },
    "aliases": {
        "dj": {
            "service": "django",
            "command": "django-admin"
        }
    },
    "docker_vars": {},
    "plugins": {
      "sync_pg_data": {
        "staging": {
          "env_file": ".env.staging",
          "args": {
            "HOST": "storefront.staging.sharptype.co",
            "PASSWORD": "$POSTGRES_PASSWORD",
            "USER": "$POSTGRES_USER",
            "NAME": "$POSTGRES_DB"
          }
        },
        "local": {
          "env_file": ".env",
          "write": true,
          "args": {
            "HOST": "localhost",
            "PASSWORD": "thisisbogus",
            "USER": "sharptype",
            "NAME": "sharptype",
            "PORT": 8887
          }
        }
      }
    }
}

```

### Usage

Usage instructions can be viewed after installation with `sykle --help`

```
Sykle CLI

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
  syk deploy [--debug] [--config=<file>] [--env=<env_file>] [--location=<location>]
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
  plugins*            (option) hash containing plugin specific configuration

```

### Development

The README for the main package and each plugin is generated via mustache (actual README.md files are read only). This allows us to insert the docstrings (which determine command line arguments) into each README so they stay up to date automatically.

When you pull down the repo for the first time, you should run the following command:

```sh
git config core.hooksPath .githooks
```

This will make it so that after commit, if there has been a change to the docstrings, an additional "Update README" commit will be created with up to date documentation

#### Writing plugins

1. Create a folder in `/plugins` (name of this folder will be the name of your plugin)
2. Create a class named `Plugin` that implements `src.plugins.IPlugin` and uses `docopt` (See existing plugins for examples)
3. Import/define that `Plugin` class in `__init__.py` (plugin must be accessible from root via 'import "plugins.<nameofplugin>.Plugin"')

Any `README.mustache` defined in a plugin folder will have a usage variable provided to it, and will result in a `README.md` being created when code is commited

### Roadmap

- [x] Move to separate repo
- [x] Allow user to specify `test` commands
- [x] Add plugins
- [x] REAMDE.md generation on ~push to repo~ commit
- [x] Add `init` command to create `.sykle.json`
- [ ] Terraform support
- [ ] Revisit whether `docker-compose` files can/should be shared
