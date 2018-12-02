"""Sync PG Data

Usage:
  syk sync_pg_data recreate --dest=<name> [--debug]
  syk sync_pg_data restore --dest=<name> [--file=<name>] [--debug]
  syk sync_pg_data dump --src=<name> [--debug]
  syk sync_pg_data --src=<name> --dest=<name> [--debug]

Options:
  -h --help         Show help info
  --version         Show version
  --src=<name>      Specify where to pull data from
  --dest=<name>     Specify where to push data to
  --debug           Print debug information
  --file=<name>     Restore from a file

Description:
  recreate          Drops and then recreates a database (with data)
  dump              Dumps data to a file
  restore           Restores from a file

Example .sykle.json:
  {
     "plugins": {
        "sync_pg_data": {
            "dependent_services": [],    // List of any services that should be
                                         // stopped while syncing and restarted
                                         // afterwards. (OPTIONAL)

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

__version__ = '0.1.0'

from sykle.call_subprocess import call_subprocess
from sykle.plugin_utils import IPlugin
from sykle.config import Config
from docopt import docopt
from datetime import datetime
import os


class Plugin(IPlugin):
    REQUIRED_ARGS = ['USER', 'HOST', 'NAME', 'PASSWORD']
    NAME = 'sync_pg_data'
    dump_dir = 'backups'

    def get_dump_file_name(self, location):
        now = str(datetime.now()).replace(' ', '_')
        filename = '{}_backup_{}'.format(location, now)
        return os.path.join(self.dump_dir, filename)

    def _get_location_args(self, location_name):
        locations = self.config.get("locations", {})
        location = locations.get(location_name)
        if location is None:
            raise Exception(
                'Unknown location "{}" (check "sync_pg_data" config)'
                .format(location_name))

        env_file = location.get('env_file')
        args = location.get('args')

        if args is None:
            raise Exception(
                'Config for "{}" needs "args"!'
                .format(location_name))

        for k in Plugin.REQUIRED_ARGS:
            if k not in args:
                raise Exception(
                    'Config for "{}" is missing "{}" arg!'
                    .format(location_name, k))

        if env_file:
            args = Config.interpolate_env_values_from_file(args, env_file)

        return args

    def dump(self, location, dump_file, debug=False):
        """
        Dumps data from the given location (no contraints/tables, just data)
        """
        if not os.path.isdir(self.dump_dir):
            os.makedirs(self.dump_dir)

        args = self._get_location_args(location)
        print('Dumping "{}" to "{}"...'.format(location, dump_file))
        call_subprocess(
            command=[
                'pg_dump', '-h', args['HOST'],
                '-v', '-U', args['USER'], args['NAME'],
                '-p', str(args.get('PORT', 5432)),
                '-f', dump_file,
                '--format', 'tar'
            ],
            env={'PGPASSWORD': str(args['PASSWORD'])},
            debug=debug
        )
        print('Dumped "{}" to "{}".'.format(location, dump_file))

    def restore(self, location, restore_file, debug=False):
        """
        Restores data to the given location. (requires truncation)
        """
        # Double check to ensure we aren't overwriting prod
        self.check_write_permissions(location)
        args = self._get_location_args(location)
        print('Restoring "{}" to "{}"...'.format(restore_file, location))
        call_subprocess(
            command=[
                'pg_restore', '--verbose', '--host', args['HOST'],
                '--username', args['USER'],
                '--port', str(args.get('PORT', 5432)),
                '--dbname', args['NAME'],
                restore_file
            ],
            env={'PGPASSWORD': str(args['PASSWORD'])},
            debug=debug
        )
        print('Restored "{}" to "{}".'.format(restore_file, location))

    def recreate(self, location, debug=False):
        """
        Deletes all data in the given location.
        """
        # Double check to ensure we aren't deleting write protected data
        self.check_write_permissions(location)
        args = self._get_location_args(location)

        print('Droping "{}"...'.format(location))
        call_subprocess(
            command=[
                'dropdb', '--host', args['HOST'],
                '--username', args['USER'],
                '--port', str(args.get('PORT', 5432)),
                args['NAME']
            ],
            env={'PGPASSWORD': str(args['PASSWORD'])},
            debug=debug
        )
        print('Dropped "{}".'.format(location))
        print('Creating "{}"...'.format(location))
        call_subprocess(
            command=[
                'createdb', '--host', args['HOST'],
                '--username', args['USER'],
                '--port', str(args.get('PORT', 5432)),
                args['NAME']
            ],
            env={'PGPASSWORD': str(args['PASSWORD'])},
            debug=debug
        )
        print('Created "{}".'.format(location))

    def confirm_delete(self, location):
        return input(
            "This will delete all data in '{}'.\nContinue? (y/n): "
            .format(location)) == 'y'

    def confirm_dump(self, dump_file):
        if os.path.isfile(dump_file):
            return input(
                "'{}' will be overwritten.\nContinue? (y/n): "
                .format(dump_file)) == 'y'
        return True

    def confirm_restore(self, restore_file, location):
        if not restore_file:
            raise Exception('No restore file!')
        if not os.path.isfile(restore_file):
            raise Exception('{} does not exist!'.format(restore_file))
        return input(
            "Restore '{}' to '{}'? (y/n): "
            .format(restore_file, location)) == 'y'

    def check_write_permissions(self, location):
        locations = self.config.get("locations", {})
        if not locations.get(location).get('write'):
            raise Exception(
                'Cannot delete/write data to "{}" '.format(location) +
                '("write" is not set to true)')

    def most_recent_backup(self):
        files = [f for f in os.listdir(self.dump_dir)]
        files.sort()
        return os.path.join(self.dump_dir, files[-1]) if files else None

    def run(self):
        args = docopt(__doc__, version=__version__)
        src = args.get('--src')
        dest = args.get('--dest')
        debug = args.get('--debug')
        self.sykle.debug = debug

        dependent_services = self.config.get("dependent_services", [])
        for service in dependent_services:
            self.sykle.dc(["stop", service])

        if args['recreate']:
            self.check_write_permissions(dest)
            if self.confirm_delete(dest):
                self.recreate(dest, debug)
        elif args['restore']:
            self.check_write_permissions(dest)
            file = args['--file'] or self.most_recent_backup()
            if self.confirm_restore(file, dest) and self.confirm_delete(dest):
                self.recreate(dest, debug)
                self.restore(dest, file, debug)
        elif args['dump']:
            dump_file = self.get_dump_file_name(src)
            if self.confirm_dump(dump_file):
                self.dump(src, dump_file, debug)
        else:
            self.check_write_permissions(dest)
            dump_file = self.get_dump_file_name(src)
            if self.confirm_delete(dest) and self.confirm_dump(dump_file):
                self.dump(src, dump_file, debug)
                self.recreate(dest, debug)
                self.restore(dest, dump_file, debug)

        for service in dependent_services:
            self.sykle.dc(["start", service])
