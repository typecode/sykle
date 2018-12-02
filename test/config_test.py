from sykle.config import Config
from unittest.mock import patch
import unittest


class ConfigTestCase(unittest.TestCase):
    @patch('os.environ', {'ENV_VAR': 'a'})
    def test_docker_vars_for_depolyment(self):
        config = Config(
            project_name='test', default_service='app',
            default_deployment='staging', deployments={
                'staging': {
                    'target': 'some-target',
                    'docker_vars': {
                        'non_env_var': u'thing',
                        'env_var': u'$ENV_VAR'
                    }
                }
            }
        )
        docker_vars = config.docker_vars_for_deployment('staging')
        self.assertEqual(docker_vars, {
            'non_env_var': 'thing', 'env_var': 'a'
        })

    def test_for_deployment_empty(self):
        config = Config(
            project_name='test', default_service='app',
            default_deployment='staging'
        )
        with self.assertRaises(Config.UnknownDeploymentException):
            config.for_deployment('staging')

    def test_interpolate_env_values(self):
        interpolated = Config.interpolate_env_values(
            {'non_env_var': 'A', 'env_var': u'$BUILD_NUMBER'},
            {u'BUILD_NUMBER': u'1'}
        )
        self.assertEqual(
            interpolated,
            {'non_env_var': 'A', 'env_var': '1'},
        )

    def test_interpolate_empty_env_values(self):
        interpolated = Config.interpolate_env_values(
            {'non_env_var': 'A', 'env_var': '$BUILD_NUMBER'},
            {}
        )
        self.assertEqual(
            interpolated,
            {'non_env_var': 'A', 'env_var': ''},
        )
