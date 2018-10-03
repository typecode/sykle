"""Sync PG Data

Usage:
  syk sync_pg_data [--src=<name>] [--dest=<name>] [--debug]

Options:
  -h --help         Show help info
  --version         Show version
  --src=<name>      Specify where to pull data from
  --dest=<name>     Specify where to push data to
  --debug           Print debug information

Example .sykle.json:
  {
     "plugins": {
        "sync_pg_data": {
            "local": {                   // Name of location
                "env_file": ".env",      // Envfile for args to use (OPTIONAL)
                "write": true,           // Allow writes to location
                "args": {
                   "PORT": 5432,         // Port for postgres (OPTIONAL)
                   "HOST": "$PG_HOST",   // Host for postgres
                   "USER": "postgres",   // Username for postgres
                   "PASSWORD": "asdf"    // Password for postgres
                }
            }
        }
     }
  }
"""

__version__ = '0.0.1'

from src.call_subprocess import call_subprocess
from src.plugins import IPlugin
from src.config import Config
from docopt import docopt
import os


class Plugin(IPlugin):
    REQUIRED_ARGS = ['USER', 'HOST', 'NAME', 'PASSWORD']
    name = 'sync_pg_data'
    temp_dump_file = 'dump.sql'

    def _get_location_args(self, location_name):
        location = self.config.get(location_name)
        if location is None:
            raise Exception('Unknown location "{}" (check "sync_pg_data" config)'.format(location_name))

        env_file = location.get('env_file')
        args = location.get('args')

        if args is None:
            raise Exception('Config for "{}" needs "args"!'.format(location_name))

        for k in Plugin.REQUIRED_ARGS:
            try:
                args[k]
            except KeyError:
                raise Exception('Config for "{}" is missing "{}" arg!'.format(location_name, k))

        if env_file:
            args = Config.interpolate_env_values_from_file(args, env_file)
        return args

    def dump(self, args, debug=False):
        call_subprocess(
            command=[
                'pg_dump', '-C', '-h', args['HOST'],
                '-v', '-U', args['USER'], args['NAME'],
                '-p', str(args.get('PORT', 5432)),
                '-f', self.temp_dump_file
            ],
            env={'PGPASSWORD': str(args['PASSWORD'])},
            debug=debug
        )

    def restore(self, args, debug=False):
        call_subprocess(
            command=[
                'psql', '-h', args['HOST'],
                '-U', args['USER'], args['NAME'],
                '-p', str(args.get('PORT', 5432)),
                '-f', self.temp_dump_file
            ],
            env={'PGPASSWORD': str(args['PASSWORD'])},
            debug=debug
        )

    def run(self):
        args = docopt(__doc__, version=__version__)
        src_args = self._get_location_args(args['--src'])
        dest_args = self._get_location_args(args['--dest'])

        if not self.config.get(args['--dest']).get('write'):
            raise Exception('Cannot copy data to "{}" ("WRITE" is not set to true)'.format(args['--dest']))

        self.dump(src_args, args['--debug'])
        self.restore(dest_args, args['--debug'])
        os.remove(self.temp_dump_file)
