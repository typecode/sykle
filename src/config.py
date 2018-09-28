import json
import dotenv


class Config():
    REQUIRED_VERSION = 1
    WEBSITE = 'https://github.com/typecode/sykle'

    @staticmethod
    def from_file(filename):
        with open(filename) as f:
            config = json.load(f)
            version = config.get('version')
            if version != Config.REQUIRED_VERSION:
                print((
                    '\033[93m' +
                    'Expected config file with version="{}", not "{}".\n' +
                    '(see {})' +
                    '\033[0m'
                ).format(Config.REQUIRED_VERSION, version, Config.WEBSITE))

            # Below is to remain compatible with config files in v-0 format
            if config.get('deployment_target'):
                config['default_deployment'] = '__OLD_DEPLOYMENT__'
                deployments = config.get('deployments', {})
                deployments['__OLD_DEPLOYMENT__'] = {
                    'env_file': '.env',
                    'target': config['deployment_target'],
                }
                config['deployments'] = deployments
                config.pop('deployment_target')

            return Config(**config)

    @staticmethod
    def interpolate_env_values(dict, env):
        """
        Takes a dictionary and substitutes values prepended with '$'
        with their associated env vars
        """
        new_dict = {}
        for (k, v) in dict.items():
            if not isinstance(v, str) or v[0] != '$':
                new_dict[k] = v
            else:
                new_dict[k] = env.get(v[1:])
        return new_dict

    @staticmethod
    def interpolate_env_values_from_file(dict, env_file):
        with open(env_file):
            return Config.interpolate_env_values(
                dict, dotenv.dotenv_values(env_file)
            )

    def __init__(
        self, project_name, default_service, default_deployment, plugins={},
        docker_vars={}, aliases={}, unittest=[], e2e=[], predeploy=[],
        deployments={},
    ):
        self.project_name = project_name
        self.docker_vars = docker_vars
        self.default_deployment = default_deployment
        self.default_service = default_service
        self.aliases = aliases
        self.unittest = unittest
        self.e2e = e2e
        self.predeploy = predeploy
        self.deployments = deployments
        self.plugins = plugins

    def for_plugin(self, name):
        return self.plugins.get(name, {})

    def for_deployment(self, name):
        if name == 'local':
            return {}

        deployment = self.deployments.get(name)
        if not deployment:
            raise Exception('Unknown deployment "{}"'.format(name))
        if not deployment.get('target'):
            raise Exception('Deployment "{}" has no target!'.format(name))

        env_file = deployment.get('env_file')
        env_values = {}

        if env_file:
            with open(env_file):
                env_values = dotenv.dotenv_values(env_file)
        deployment['env_values'] = env_values
        return deployment
