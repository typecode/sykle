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
