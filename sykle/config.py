import json
import dotenv
import os
import collections


class ConfigException(Exception):
    pass


class Command:
    """
    Config for defining a command on an option docker service.
    """
    def __init__(self, command, service=None):
        self.service = service
        self.command = command

    def run(
        self, docker_compose, input=[],
        env={}, target=None, debug=False
    ):
        input = [] if not input else input
        return docker_compose.run(input=input)


class Config():
    def __init__(self, json):
        self.json = json

    @property
    def unittest(self):
        """
        Config for running unit tests. Must return an array of Command Configs
        """
        return []

    @property
    def e2e(self):
        """
        Config for running e2e tests. Must return an array of Command Configs
        """
        return []

    @property
    def run_alias




class ConfigV1():
    REQUIRED_VERSION = 2
    WEBSITE = 'https://github.com/typecode/sykle'
    FILENAME = '.sykle.json'
    CONFIG_FILE_EXAMPLE = """
{
    // specifies which version of .sykle.json is being used
    "version": 2,
    // name of the project (used when naming docker images)
    "project_name": "cool-project",
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
"""

    class ConfigFileNotFoundException(ConfigException):
        pass

    class ConfigFileDecodeException(ConfigException):
        pass

    class ConfigFileVersionException(ConfigException):
        pass

    class UnknownDeploymentException(ConfigException):
        pass

    class InvalidDeploymentException(ConfigException):
        pass

    @staticmethod
    def init(enable_print=False):
        """
        Generates a .sykle.json if one doesn't yet exist
        """
        if os.path.isfile(Config.FILENAME):
            if enable_print:
                print(
                    '\033[93m' +
                    '"{}" already exsits' +
                    '\033[0m'
                    .format(Config.FILENAME)
                )
        else:
            with open(Config.FILENAME, 'w+') as file:
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
                    .format(Config.FILENAME)
                )

    @staticmethod
    def from_file(filename):
        """
        Creates a config object from the file specified
        """
        if not os.path.isfile(filename):
            raise Config.ConfigFileNotFoundException()

        with open(filename) as f:
            config = None
            try:
                config = json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise Config.ConfigFileDecodeException(e.message)
            version = config.get('version')
            if version != Config.REQUIRED_VERSION:
                print((
                    '\033[93m' +
                    'Expected config file with version="{}", not "{}".\n' +
                    '(run "syk config" to see an example of expected config)' +
                    '\033[0m'
                ).format(Config.REQUIRED_VERSION, version))
            try:
                return Config(**config)
            except TypeError as e:
                raise Config.ConfigFileDecodeException(e.message)

    @staticmethod
    def interpolate_env_values(dict, env):
        """
        Takes a dictionary and substitutes values prepended with '$'
        with the values in the dictionary of the env parameter

        EX: interpolate_env_values({'k': '$test'}, {'test': 1}) => {'k': 1}
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
        """
        Like interpolate_env_values, but instead of using a dictionary of env
        values, will use an env file
        """
        with open(env_file):
            return Config.interpolate_env_values(
                dict, dotenv.dotenv_values(env_file)
            )

    @staticmethod
    def validate_command_configs(self, keyword, command_configs=[]):
        for command_config in command_configs:
            if not command_config.get('command'):
                Config.ConfigFileDecodeException(
                    'Command config for {} defined without a command!'
                    .format(keyword)
                )

    def __init__(
        self, project_name, default_service, default_deployment, plugins={},
        aliases={}, unittest=[], e2e=[], predeploy=[], preup=[],
        deployments={}, version=None,
    ):
        self.version = version
        self.project_name = project_name
        self.default_deployment = default_deployment
        self.default_service = default_service
        self.aliases = aliases
        self.unittest = self.validate_command_configs('unittest', unittest)
        self.e2e = self.validate_command_configs('e2e', e2e)
        self.predeploy = self.validate_command_configs('predeploy', predeploy)
        self.preup = self.validate_command_configs('preup', preup)
        self.deployments = deployments
        self.plugins = plugins

    def docker_vars_for_deployment(self, name):
        return Config.interpolate_env_values(
            self.for_deployment(name).get('docker_vars', {}),
            os.environ
        )

    def for_plugin(self, name):
        """
        Loads the configuration for a given plugin
        """
        return self.plugins.get(name, {})

    def for_deployment(self, name):
        """
        Loads the configuration for a given deployment
        """
        if name == 'local':
            return {}

        deployment = self.deployments.get(name)
        if not deployment:
            raise Config.UnknownDeploymentException(
                'Unknown deployment "{}"'.format(name)
            )
        if not deployment.get('target'):
            raise Config.InvalidDeploymentException(
                'Deployment "{}" has no target!'.format(name)
            )

        env_file = deployment.get('env_file')
        env_values = {}

        if env_file:
            with open(env_file):
                env_values = dotenv.dotenv_values(env_file)
        deployment['env_values'] = env_values
        return deployment
