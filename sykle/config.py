import os
import json
import collections
import dotenv


class CommandList(list):
    @staticmethod
    def from_json(arr):
        return list(map(lambda obj: Command.from_json(obj), arr))

    def for_service(self, service):
        return list(filter(lambda command: command.service == service, self))


class Command:
    @staticmethod
    def from_json(obj):
        return Command(
            input=obj.get('command'),
            service=obj.get('service'),
            docker_type=obj.get('env', 'dev')
        )

    def __init__(self, input, service=None, docker_type='dev'):
        self.service = service
        self.input = input.split(' ') if type(input) == str else input
        self.docker_type = docker_type

    def __str__(self):
        return "(Service: \"{}\", Input: \"{}\", Env: \"{}\")".format(
            self.service,
            ' '.join(self.input),
            self.docker_type
        )


class DeploymentConfig:
    @staticmethod
    def from_json(obj):
        return DeploymentConfig(
            target=obj.get('target'),
            env_file=obj.get('env_file'),
            docker_vars=obj.get('docker_vars')
        )

    def __init__(self, target, env_file, docker_vars={}):
        self.target = target
        self.env_file = env_file
        self.docker_vars = docker_vars


class Config():
    REQUIRED_VERSION = 2
    FILENAME = '.sykle.json'

    class ConfigException(Exception):
        pass

    class ConfigFileNotFoundException(ConfigException):
        pass

    class ConfigFileDecodeException(ConfigException):
        pass

    class InvalidConfigException(ConfigException):
        pass

    class UnknownDeploymentException(ConfigException):
        pass

    class UnknownAliasException(ConfigException):
        pass

    class InvalidDeploymentException(ConfigException):
        pass

    @staticmethod
    def print_example(self):
        print(ConfigV2.CONFIG_FILE_EXAMPLE)

    @staticmethod
    def interpolate_env_values(dict, env):
        """
        Takes a dictionary and substitutes values prepended with '$'
        with their associated env vars
        """
        new_dict = {}
        for (k, _v) in dict.items():
            v = '' if _v is None else str(_v)
            if len(v) == 0:
                new_dict[k] = ''
            elif v[0] != '$':
                new_dict[k] = v
            else:
                new_dict[k] = env.get(v[1:], '')
        return new_dict

    @staticmethod
    def interpolate_env_values_from_file(dict, env_file):
        with open(env_file):
            return Config.interpolate_env_values(
                dict, dotenv.dotenv_values(env_file)
            )

    @staticmethod
    def init(*args, **kwargs):
        return ConfigV2.init(*args, **kwargs)

    @staticmethod
    def from_file(filename):
        if not os.path.isfile(filename):
            raise Config.ConfigFileNotFoundException()

        with open(filename) as f:
            config = None
            try:
                config = json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise Config.ConfigFileDecodeException(
                    "Error decoding json: {}".format(e)
                )

            if config.get('version') == 2:
                try:
                    return ConfigV2(raw=config)
                except TypeError as e:
                    raise Config.InvalidConfigException(
                       "Error initializing config: {}".format(e)
                    )
            else:
                raise Config.InvalidConfigException(
                    "Invalid config version: {}".format(config.get('version'))
                )

    @property
    def e2e_commands(self):
        raise NotImplementedError()

    @property
    def unittest_commands(self):
        raise NotImplementedError()

    @property
    def predeploy_commands(self):
        raise NotImplementedError()

    def has_alias(self, alias):
        raise NotImplementedError()

    def get_alias_command(self, alias):
        raise NotImplementedError()

    def for_plugin(self, name):
        raise NotImplementedError()

    def for_deployment(self, name):
        raise NotImplementedError()


class ConfigV2(Config):
    FILENAME = '.sykle.json'
    CONFIG_FILE_EXAMPLE = """
{
    // specifies which version of .sykle.json is being used
    "version": 2,
    // name of the project
    "project_name": "tc-project",
    // docker compose service to use for commands by default
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
    // list of commands to invoke before deploy (run sequentially)
    "predeploy": [
        {
            "service": "django",
            "command": "django-admin collectstatic --no-input"
        },
        {
            // if no service is specified, will run as normal bash command
            "command": "aws ecr get-login --region us-east-1"
        }
    ],
    // list of commands to invoke before up (run sequentially)
    "preup": [
        {
            // if no service is specified, will run as normal bash command
            "command": "syk down"
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
            "target": "ec2-user@staging.my-site.com",
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
        },
        "behave": {
          "service": "backend",
          "command": "behave --no-capture --no-skipped",
          // when env is specified, alias is run using the corresponding
          // docker compose file
          "env": "test"
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
"""

    def __init__(self, raw):
        self.raw = raw

    @staticmethod
    def init(enable_print=False):
        if os.path.isfile(ConfigV2.FILENAME):
            if enable_print:
                print(
                    '\033[93m' +
                    '"{}" already exsits' +
                    '\033[0m'
                    .format(ConfigV2.FILENAME)
                )
        else:
            with open(ConfigV2.FILENAME, 'w+') as file:
                json.dump(collections.OrderedDict([
                    ("version", 2),
                    ("project_name", None),
                    ("default_service", None),
                    ("unittest", [{"service": None, "command": None}]),
                    ("e2e", [{"service": None, "command": None}]),
                    ("predeploy", []),
                    ("preup", []),
                    ("default_deployment", "staging"),
                    ("deployments", {
                        "staging": {
                            "env_file": '.env.staging',
                            "target": None,
                            "docker_vars": {}
                        },
                        "prod": {
                            "env_file": '.env.prod',
                            "target": None,
                            "docker_vars": {}
                        },
                    }),
                    ("aliases", {}),
                    ("plugins", {})
                ]), file, indent=2)
            if enable_print:
                print(
                    '\033[92m' +
                    '"{}" created!' +
                    '\033[0m'
                    .format(ConfigV2.FILENAME)
                )

    def get_project_name(self, docker_type='dev'):
        if docker_type in ['dev', 'test']:
            return os.path.basename(os.getcwd())
        else:
            return self.raw.get('project_name', 'tc-project')

    @property
    def default_service(self):
        return self.raw.get('default_service')

    @property
    def unittest_commands(self):
        return CommandList.from_json(self.raw.get('unittest', []))

    @property
    def e2e_commands(self):
        return CommandList.from_json(self.raw.get('e2e', []))

    @property
    def predeploy_commands(self):
        return CommandList.from_json(self.raw.get('predeploy', []))

    @property
    def preup_commands(self):
        return CommandList.from_json(self.raw.get('preup', []))

    @property
    def default_deployment(self):
        return self.raw.get('default_deployment')

    def has_alias(self, alias):
        return alias in self.raw.get('aliases', {}).keys()

    def get_alias_command(self, alias, input=[]):
        if not self.has_alias(alias):
            raise Config.UnknownAliasException(
                'Unknown alias "{}"'.format(alias)
            )
        command = Command.from_json(self.raw.get('aliases')[alias])
        command.input += input
        return command

    def for_plugin(self, name):
        plugins = self.raw.get('plugins', {})
        return plugins.get(name, {})

    def for_deployment(self, name):
        deployments = self.raw.get('deployments', {})
        deployment_json = deployments.get(name)
        if not deployment_json:
            raise Config.UnknownDeploymentException(
                'Unknown deployment "{}"'.format(name)
            )
        if not deployment_json.get('target'):
            raise Config.InvalidDeploymentException(
                'Deployment "{}" has no target!'.format(name)
            )

        return DeploymentConfig.from_json(deployment_json)
