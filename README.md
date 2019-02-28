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

Because sykle tries to make as few assumptions about your project as possible, you'll need to declaratively define how your app should run via static configuration files

#### Docker Compose

Sykle uses 4 different docker-compose configurations:

- `docker-compose.yml` for development
- `docker-compose.test.yml` for testing
- `docker-compose.prod-build.yml` for building/deploying production
- `docker-compose.prod.yml` for running production

These separate configurations allow you to tweak how your projects run in those 4 standard scenarios, and helps ensure that there no conflicting assumptions between environments.

#### .sykle.json

In addition to your `docker-compose` files, you'll need a `.sykle.json`. An example detailing how to build a config file can be viewed from the cli via `syk config`

### Usage

Usage instructions can be viewed after installation with `syk --help`

This will not show any info for plugins. In order to view installed plugins, run `syk plugins`. To view help for a specfic plugin, run `syk <plugin_name> --help`.

### Legacy ./run.sh

Prior to sykle, the predominate pattern at typecode was to create a `./run.sh` file with a list of commands. For convenience, if a `./run.sh` file is found, sykle will try to run commands through `./run.sh` before running through sykle.

### Connecting to Deployments

Once you have configured deployments, you can connect to them using `syk --deployment=<deployment> ssh`. Sykle does not currently allow you pass any options when sshing into a remove machine and relies on `~/.ssh/config` to pass along the correct credentials. An example config is shown below, and more details on ssh config can be found [here](https://linuxize.com/post/using-the-ssh-config-file/).

```
Host ec2-3-95-177-93.compute-1.amazonaws.com
  User ubuntu
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/flir-pb.pem
```

### Running Tests (for sykle)

Unittests (that test sykle) can be run via `python setup.py test`

### Writing plugins

There are two types of plugins: **global** plugins and **local** plugins.

#### Local Plugins

Local plugins allow you to create project specific commands. If you have a command or series of commands that you run frequently for a project that are more complicated than an alias, it might make sense to create a local plugin.

To create a local plugin:

1. Create a `.sykle-plugins/` directory in the root of your project (`.sykle-plugins/` should be in same directory as `.sykle.json`)
2. Add an `__init__.py` file to `.sykle-plugins/`
3. Add a python file for your plugin to `.sykle-plugins/` (EX: `.sykle-plugins/my_plugin.py`)
4. Define your plugin like in the example below:

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

#### Global Plugins

Global plugins are the same as local plugins, but they are added to the `plugins` folder of this repo and are available to anyone who installs sykle.

### Roadmap

- [x] Move to separate repo
- [x] Allow user to specify `test` commands
- [x] Add plugins
- [x] Add `init` command to create `.sykle.json`
- [x] ~Scripts section in `.sykle.json`~ Local plugins
-  ~REAMDE.md generation on commit~ (unecessarily complex)
- [x] Fallback to `./run.sh` if it exists and `.sykle.json` does not
- [ ] User aliases/way to share aliases
- [ ] Terraform support
- [ ] Revisit whether `docker-compose` files can/should be shared
