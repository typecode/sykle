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
- Does not generate DockerFiles, Docker-Compose files, etc
- Does not replace standard devops tools
  - (plugins should delegate to other tools)

### Requirements

- `python 3.4` (may work on earlier versions of 3, but not tested. Plugins do NOT work in python version 2.7)
- `docker` (locally and on deployment target)
- `docker-compose` (locally and on deployment target)
- `ssh`
- `scp`

### Installation

#### If python3 is your default installation, you can use pip

`pip install git+ssh://git@github.com/typecode/sykle.git --upgrade`

#### If you have a separate `python3` installation, you should use pip3

`pip3 install git+ssh://git@github.com/typecode/sykle.git --upgrade`

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

In addition to your `docker-compose` files, you'll need a `.sykle.json`. An example is listed below. This example can be viewed from the cli via `syk config`

*Example:*
```js

{
    // specifies which version of .sykle.json is being used
    "version": 2,
    // name of the project (used when naming docker images)
    "project_name": "cool-project",
    // docker compose service to use for commands by default (EX: for syk dc_run)
    "default_service": "django",
    // list of commands needed to run unittests (run sequentially)
    "unittest": [
        {
            // docker compose service on which to run the command
            "service": "django",
            // command invoked via 'docker-compose run --rm <service>'
            "command": "django-admin test"
        },
        {
            "service": "node",
            "command": "npm test"
        }
    ],
    // list of commands needed to run e2e tests (run sequentially)
    "e2e": [
        {
            "service": "django",
            "command": "behave"
        }
    ],
    // list of commands to invoke before deploying (run sequentially)
    "predeploy": [
        {
            "service": "django",
            "command": "django-admin collectstatic --no-input"
        }
    ],
    // deployment to use by default (must be listed in deployments section)
    "default_deployment": "staging",
    // a collection of locations where you can deploy the project to.
    // each remote instance is assumed to:
    //   - be accessible via ssh
    //   - have docker installed
    //   - have docker-compose installed
    // the machine you are deploying from is assumed to:
    //   - have ssh access to the remote machine
    //   - have the 'ssh' command
    //   - have the 'scp' command
    //   - have docker installed
    //   - have docker-compose installed
    "deployments": {
        // the location of the deployment (EX: 'syk --location=prod deploy')
        "prod": {
            // the ssh address of the machine the deployment should point to
            "target": "ec2-user@www.my-site.com",
            // environment to use when the deployment is running
            "env": ".env.prod",
            // docker_vars are variables that are made available to the
            // prod-build and prod docker compose files
            "docker_vars": {
              "SERVICE_IMAGE": "some-ecr-url/prod-repo",
              // if a variable begins with a $ sign, it will pull the value
              // from that environment value
              "BUILD_NUMBER": "$BUILD_NUMBER"
            }
        },
        // multiple deployments can be listed
        "staging": {
            "target": "ect-user@staging.my-site.com",
            "env": ".env.staging",
            "docker_vars": {
              "SERVICE_IMAGE": "some-ecr-url/staging-url",
              "BUILD_NUMBER": "$BUILD_NUMBER"
            }
        }
    },
    // defines shortcuts for commonly used commands
    "aliases": {
        // name of the command (would type 'syk dj <INPUT>' to use)
        "dj": {
            "service": "django",
            "command": "django-admin"
        }
    },
    // defines settings specific to plugins
    "plugins": {
      // name of the plugin the settings apply to
      "sync_pg_data": {
        "locations": {
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
}

```

### Usage

Usage instructions can be viewed after installation with `syk --help`

This will not show any info for plugins. In order to view installed plugins, run `syk plugins`. To view help for a specfic plugin, run `syk <plugin_name> --help`.

```
Sykle CLI
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

```

### Development

The README for the main package and each global plugin is generated via mustache (actual README.md files are read only). This allows us to insert the docstrings (which determine command line arguments) into each README so they stay up to date automatically.

When you pull down the repo for the first time, you should run the following command:

```sh
git config core.hooksPath .githooks
```

This will make it so that after commit, if there has been a change to the docstrings, an additional "Update README" commit will be created with up to date documentation.

#### Githook Requirements

You will need to install `chevron` for the githooks to work:

```sh
pip install chevron
```

#### Running Tests

Unittests can be run via `python setup.py test`

#### Writing plugins

There are two types of plugins: **global** plugins and **local** plugins.

##### Local Plugins

Local plugins allow you to create project specific commands. If you have a command or series of commands that you run frequently for a project that are more complicated than an alias, it might make sense to create a local plugin.

To create a local plugin:

1. Create a `.sykle-plugins/` directory in the root of your project (`.sykle-plugins/` should be in same directory as `.sykle.json`)
2. Add an `__init__.py` file to `.sykle-plugins/`
3. Add a python file for your plugin to `.sykle-plugins/` (EX: `.sykle-plugins/my_plugin.py`)
4. Define your plugin like in the exapmle below:

Example
```py
"""my_plugin
Usage:
  syk my_plugin <str>

Options:
  -h --help                     Show help info

Description:
  my_plugin                     prints out the string passed in as an argument
"""
from docopt import docopt
from sykle.plugin_utils import IPlugin


class Plugin(IPlugin): # class MUST be named Plugin
    NAME = 'my_plugin' # this attribue is required
    REQUIRED_VERSION = '0.3.0' # this attribute is option (specifies lowest version of sykle required)

    # this is what gets invoked when you run `syk my_plugins hi`
    def run(self):
        args = docopt(__doc__)
        str = args.get('<str>')
        # self.sykle        <- sykle instance
        # self.sykle_config <- config used by sykle instance
        # self.config       <- any config specific to this plugin
        print(str)
```

Note that `syk` is present in the docopt usage definition before the plugin command. This is required.

If you defined your plugin correctly, you should be able to see listed when calling `syk plugins`

##### Global Plugins

Global plugins are the same as local plugins, but they are added to the `plugins` folder of this repo and are available to anyone who installs sykle.

Any `README.mustache` defined in a plugin folder will have a usage variable provided to it, and will result in a `README.md` being created when code is commited

### Roadmap

- [x] Move to separate repo
- [x] Allow user to specify `test` commands
- [x] Add plugins
- [x] REAMDE.md generation on ~push to repo~ commit
- [x] Add `init` command to create `.sykle.json`
- [ ] Fallback to `./run.sh` if it exists and `.sykle.json` does not
- [x] ~Scripts section in `.sykle.json`~ Local plugins
- [ ] User aliases/way to share aliases
- [ ] Terraform support
- [ ] Revisit whether `docker-compose` files can/should be shared
