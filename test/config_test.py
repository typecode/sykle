from sykle.config import ConfigV2
import unittest


class ConfigTestCase(unittest.TestCase):
    def test_for_deployment_empty(self):
        config = ConfigV2({
            'project_name': 'test',
            'default_service': 'app',
            'default_deployment': 'staging'
        })
        with self.assertRaises(ConfigV2.UnknownDeploymentException):
            config.for_deployment('staging')

    def test_interpolate_env_values(self):
        interpolated = ConfigV2.interpolate_env_values(
            {'non_env_var': 'A', 'env_var': u'$BUILD_NUMBER'},
            {u'BUILD_NUMBER': u'1'}
        )
        self.assertEqual(
            interpolated,
            {'non_env_var': 'A', 'env_var': '1'},
        )

    def test_interpolate_empty_env_values(self):
        interpolated = ConfigV2.interpolate_env_values(
            {'non_env_var': 'A', 'env_var': '$BUILD_NUMBER'},
            {}
        )
        self.assertEqual(
            interpolated,
            {'non_env_var': 'A', 'env_var': ''},
        )
