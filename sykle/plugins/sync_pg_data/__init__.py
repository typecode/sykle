"""Sync PG Data

Usage:
  syk sync_pg_data truncate --dest=<name> [--debug]
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
  truncate          Removes all data on db
  restore           Restores from a file
  dump              Dumps data to a file

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

__version__ = '0.0.3'

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
        location = self.config.get(location_name)
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
                'pg_dump', '-C', '-h', args['HOST'],
                '-v', '-U', args['USER'], args['NAME'],
                '-p', str(args.get('PORT', 5432)),
                '-f', dump_file,
                '--data-only',
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
                '--disable-triggers', restore_file,
                '--data-only'
            ],
            env={'PGPASSWORD': str(args['PASSWORD'])},
            debug=debug
        )
        print('Restored "{}" to "{}".'.format(restore_file, location))

    def truncate(self, location, debug=False):
        """
        Deletes all data in the given location. (Does NOT drop tables)
        """
        # Double check to ensure we aren't truncating prod
        self.check_write_permissions(location)
        args = self._get_location_args(location)
        psql_command = (
            " DO \$\$ DECLARE statements CURSOR FOR SELECT " +
            "tablename FROM pg_tables WHERE tableowner = '{}' "
            .format(args['NAME']) +
            "AND schemaname = 'public'; " +
            "BEGIN FOR stmt IN statements LOOP EXECUTE " +
            "'TRUNCATE TABLE ' || quote_ident(stmt.tablename) || '" +
            " CASCADE;'; END LOOP; END; \$\$ LANGUAGE plpgsql;"
        )

        print('Truncating "{}"...'.format(location))
        call_subprocess(
            command=[
                'psql', '--host', args['HOST'],
                '--username', args['USER'],
                '--port', str(args.get('PORT', 5432)),
                '-d', args['NAME'],
                '-c', '"{}"'.format(psql_command),
            ],
            env={'PGPASSWORD': str(args['PASSWORD'])},
            debug=debug
        )
        print('Truncated "{}".'.format(location))

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
        if not self.config.get(location).get('write'):
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

        if args['truncate']:
            self.check_write_permissions(dest)
            if self.confirm_delete(dest):
                self.truncate(dest, debug)
        elif args['restore']:
            self.check_write_permissions(dest)
            file = args['--file'] or self.most_recent_backup()
            if self.confirm_restore(file, dest) and self.confirm_delete(dest):
                self.truncate(dest, debug)
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
                self.truncate(dest, debug)
                self.restore(dest, dump_file, debug)
