from src.sykle import Sykle
from unittest.mock import MagicMock
import unittest


class SykleTestCase(unittest.TestCase):
    def test_dc_run_env_file(self):
        sykle = Sykle()
        sykle.dc = MagicMock()
        sykle._read_env_file = MagicMock(
            return_value={'env1': 'a', 'env2': 'b'}
        )

        sykle.dc_run(['some', 'command'], service='app', env_file='.env')
        sykle._read_env_file.assert_called_with('.env')
        sykle.dc.assert_called_with(
            docker_type='dev',
            docker_vars={},
            input=[
                'run', '-e', 'env1=a', '-e', 'env2=b',
                '--rm', 'app', 'some', 'command'
            ],
        )

    def test_dc_run_no_env_file(self):
        sykle = Sykle()
        sykle.dc = MagicMock()

        sykle.dc_run(['some', 'command'], service='app')
        sykle.dc.assert_called_with(
            docker_type='dev',
            docker_vars={},
            input=['run', '--rm', 'app', 'some', 'command'],
        )
