# sykle

Pretty much every project needs a way to run tests, a way to deploy, a way to build, etc. Sykle takes advantage of `docker-compose` to cut down on the setup required for those universal tasks while remaining flexible to different product requirements.

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

These separate configurations allow you to tweak how your projects run in those 4 standard scenarios, and helps ensure clean test runs, predictable builds, and conflict prevention when running different tasks in parallel.

#### .sykle.json

In addition to your `docker-compose` files, you'll need a `.sykle.json`. This tells sykle the name of your project, where to deploy it, what to do before deploying, what `docker-compose` service should be used when none is specified, how to run unit tests, and how to run end to end tests. It also provides an `aliases` section for defining shortcuts for commonly used project specific commands.

*Example:*
```json
{
    "project_name": "cool-project",
    "deployment_target": "ubuntu@some-cool-project.com",
    "default_service": "django",
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
    "aliases": {
      "dj": {
        "service": "django",
        "command": "django-admin"
      }
    },
    "predeploy": [
      {
        "service": "django",
        "command": "django-admin collectstatic --no-input"
      }
    ]
}

```

### Usage

Usage instructions can be viewed after installation with `sykle --help`

```
Sykle CLI

Usage:
  syk dc [--debug] [--config=<file>] [--test | --prod] [INPUT ...]
  syk dc_run [--debug] [--config=<file>] [--service=<service>] [--test | --prod] [INPUT ...]
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
  --test              Run test version of the command
  --prod              Run prod version of the command
  --config=<file>     Specify JSON config file [default: .sykle.json]
  --dest=<dest>       Destination path [default: ~]
  --env=<env_file>    Env file to use [default: .env]
  --service=<service> Docker service on which to run the command
  --debug             Prints debug information

Description:
  dc              Runs docker-compose command
  dc_run          Runs command on a docker-compose service
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

```

### Roadmap

- [x] Move to separate repo
- [x] Allow user to specify `test` commands
- [ ] Terraform support
- [ ] REAMDE.md generation on push to repo
- [ ] Add `init` command to create `.sykle.json`
- [ ] Revisit whether `docker-compose` files can/should be shared
