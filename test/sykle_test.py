from sykle import Sykle
from sykle.config import ConfigV2
from unittest.mock import MagicMock
import unittest


class SykleTestCase(unittest.TestCase):
    def test_dc_run_env_file(self):
        sykle = Sykle(config=ConfigV2({}))
        sykle.dc = MagicMock()

        sykle.dc_run(['some', 'command'], service='app', env_file='.env')
        sykle.dc.assert_called_with(
            env_file='.env',
            input=[
                'run', '--rm', 'app', 'some', 'command'
            ],
        )

    def test_dc_run_no_env_file(self):
        sykle = Sykle(config=ConfigV2({}))
        sykle.dc = MagicMock()

        sykle.dc_run(['some', 'command'], service='app')
        sykle.dc.assert_called_with(
            input=['run', '--rm', 'app', 'some', 'command'],
        )

    def test_deploy(self):
        config = ConfigV2({
          "project_name": "sharp-ecommerce",
          "default_service": "backend",
          "unittest": [],
          "e2e": [],
          "predeploy": [
            {
              "service": "static",
              "command": "npm run-script build"
            },
            {
              "service": "backend",
              "command": "django-admin collectstatic --no-input"
            }
          ],
          "default_deployment": "staging",
          "deployments": {
            "staging": {
              "target": "fake-target",
              "env_file": "./.env.staging",
              "docker_vars": {
                "BUILD_NUMBER": "latest"
              }
            }
          }
        })

        sykle = Sykle(config=config)
        sykle.call_subprocess = MagicMock()
        sykle.call_docker_compose = MagicMock()

        sykle.deploy('staging')
        self.assertEqual(
            sykle.call_docker_compose.mock_calls[0],
            unittest.mock.call(
                ['run', '--rm', 'static', 'npm', 'run-script', 'build'],
                project_name='sharp-ecommerce',
                debug=False,
                docker_vars={'BUILD_NUMBER': 'latest'},
                env_file='./.env.staging',
                type='prod-build'
            )
        )
        self.assertEqual(
            sykle.call_docker_compose.mock_calls[1],
            unittest.mock.call(
                [
                    'run', '--rm', 'backend', 'django-admin',
                    'collectstatic', '--no-input'
                ],
                project_name='sharp-ecommerce',
                debug=False,
                docker_vars={'BUILD_NUMBER': 'latest'},
                env_file='./.env.staging',
                type='prod-build'
            )
        )
        self.assertEqual(
            sykle.call_docker_compose.mock_calls[2],
            unittest.mock.call(
                ['push'],
                debug=False,
                docker_vars={'BUILD_NUMBER': 'latest'},
                env_file='./.env.staging',
                project_name='sharp-ecommerce',
                type='prod-build'
            )
        )
        self.assertEqual(
            sykle.call_docker_compose.mock_calls[3],
            unittest.mock.call(
                ['pull'],
                debug=False,
                docker_vars={'BUILD_NUMBER': 'latest'},
                project_name='sharp-ecommerce',
                target='fake-target',
                type='prod'
            )
        )
        self.assertEqual(
            sykle.call_docker_compose.mock_calls[4],
            unittest.mock.call(
                ['up', '--build', '--force-recreate', '-d'],
                debug=False,
                docker_vars={'BUILD_NUMBER': 'latest'},
                project_name='sharp-ecommerce',
                target='fake-target',
                type='prod'
            )
        )
