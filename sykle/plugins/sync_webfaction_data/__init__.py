"""sync_webfaction_data

Usage:
  syk sync_webfaction_data dump <location>
  syk sync_webfaction_data --src=<name> --dest=<name> [--assets]
  syk sync_webfaction_data -h | --help

Options:
  --assets                          Include assets.
  -h --help                         Show this screen.

Description:
  dump <location>                   Create a remote dump of <location>'s
                                    webfaction db.
  --src=<name> --dest=<name>        Sync src's db to dest's db. Data only.
                                    May be any combination of webfaction,
                                    remote, or local databases. dest may not
                                    be "production".

Example .sykle.json:
  {
     "plugins": {
        "sync_webfaction_data": {
            "locations": {
                "local": {                   // Name of location
                    "env_file": ".env",      // Envfile for args (OPTIONAL)
                    "write": true,           // Allow writes to location
                    "args": {
                       "PORT": 5432,         // Port for postgres (OPTIONAL)
                       "HOST": "$PG_HOST",   // Host for postgres
                       "USER": "postgres",   // Username for postgres
                       "PASSWORD": "asdf",   // Password for postgres
                       "VERSION": "10.5",    // Postgres version (assumes 10.5)
                       "NETWORK": "test"     // Host docker network (OPTIONAL),
                       "MEDIA_ROOT": "$MEDIA_ROOT"
                    }
                },
                "staging": {
                    "env_file": ".env.staging",
                    "write": true,
                    "webfaction_user": "foo",
                    "webfaction_host": "gpchicago.webfaction.com"
                    "args": {
                       "WEBFACTION_PASSWORD": "$WEBFACTION_PASSWORD"
                       "DATABASE_URL": "$DATABASE_URL",
                       "MEDIAT_ROOT": "$MEDIA_ROOT"
                    }
                }
            }
        }
     }
  }
"""

import os
import datetime

from docopt import docopt

from sykle.call_subprocess import subprocess
from sykle.config import Config
from sykle.plugins.sync_pg_data import Plugin as SyncPGDataPlugin


def glob(base_path):
    return os.path.join(base_path, "*")


def enquote(string):
    return "'%s'" % string


def timestamp():
    epoch = datetime.datetime.utcfromtimestamp(0)
    return int(
        (datetime.datetime.now() - epoch).total_seconds() * 1000.0
    )


class Location:
    def __init__(self, name, env_file=None, write=False, args={}, plugin=None):
        self.name = name
        self.env_args = Config.interpolate_env_values_from_file(
            args, env_file
        )
        self.plugin = plugin
        self.sykle = plugin.sykle

    @property
    def dump_file(self):
        if not hasattr(self, "_dump_file"):
            self._dump_file = self.plugin.get_dump_file_name(
                self.name
            )
        return self._dump_file

    @property
    def media_root(self):
        return self.env_args["MEDIA_ROOT"]

    def dump(self):
        raise NotImplementedError

    def restore(self):
        raise NotImplementedError

    def copy_assets_from(self, src):
        raise NotImplementedError


class LocalLocation(Location):
    def restore(self, dump_file):
        self.plugin.restore(self.name, dump_file)


class WebfactionLocation(Location):
    name = "webfaction"

    def __init__(
        self,
        *args,
        webfaction_host=None,
        webfaction_user=None,
        ssh_key=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.host = webfaction_host
        self.user = webfaction_user
        self.password = self.env_args["WEBFACTION_PASSWORD"]

    def sshpass_cmd(self, cmd):
        return [
            "sshpass",
            "-p",
            self.password
        ] + cmd

    @subprocess
    def ssh(self, cmd):
        return self.sshpass_cmd([
            "ssh",
            self.ssh_url,
            "-o", "IdentitiesOnly=yes"
        ] + cmd)

    @subprocess
    def scp(self, src, dest):
        return self.sshpass_cmd([
            "scp",
            "-o", "IdentitiesOnly=yes",
            "%s:%s" % (self.ssh_url, src),
            dest
        ])

    @subprocess
    def rsync(self, src, dest):
        return self.sshpass_cmd([
            "rsync",
            "-chavzP",
            "-e 'ssh -o IdentitiesOnly=yes'",
            "%s:%s" % (self.ssh_url, src),
            "--include='*/'",
            "--include='*'",
            dest
        ])

    @property
    def ssh_url(self):
        return "%s@%s" % (self.user, self.host)

    def fetch_remote_pg_dump(self):
        self.scp(
            src=self.remote_tmp_dump_location,
            dest=self.dump_file
        )

    def cleanup_remote_pg_dump(self):
        self.ssh([
            "rm",
            "-f",
            self.remote_tmp_dump_location
        ])

    def create_remote_pg_dump(self, data_only=False):
        self.ssh([
            "/usr/local/pgsql/bin/pg_dump",
            "--format", "tar",
            "--data-only" if data_only else "",
            "-f", self.remote_tmp_dump_location,
            self.env_args["DATABASE_URL"]
        ])

    @property
    def remote_tmp_dump_location(self):
        if not hasattr(self, "_remote_tmp_dump_location"):
            self._remote_tmp_dump_location = "/tmp/dump-%s.sql" % (
                timestamp()
            )
        return self._remote_tmp_dump_location

    def dump(self):
        self.plugin.ensure_dump_dir()
        self.create_remote_pg_dump()
        self.fetch_remote_pg_dump()
        self.cleanup_remote_pg_dump()

        return self.dump_file

    def restore(self, src_dump, dest_remote):
        return self.ssh(dest_remote) + [
            "/usr/local/pgsql/bin/pg_restore",
            "--role=%s" % dest_remote["PG_USER"],
            "--clean",
            "--no-owner",  # The deployment databases usually have different
                           # owners. This flag specifies that the original
                           # ownership be ignored.
            "-d", dest_remote["PG_URL"],
            src_dump,
        ]

    def copy_assets_to(self, dest):
        return self.rsync(
            src=enquote(
                glob(self.media_root)
            ),
            dest=dest.media_root
        )


class LocationFactory:
    def __new__(self, name, plugin):
        locations = plugin.config.get("locations", {})
        kwargs = locations.get(name)

        if "webfaction_user" in kwargs:
            klass = WebfactionLocation
        elif name == "local":
            klass = LocalLocation

        return klass(name=name, plugin=plugin, **kwargs)


class Plugin(SyncPGDataPlugin):
    NAME = "sync_webfaction_data"
    REQUIRED_VERSION = "0.3.0"

    def run(self):
        args = docopt(__doc__)
        location = args.get("<location>", None)
        assets = args.get("--assets")

        if args.get("dump", None) and location:
            LocationFactory(location, self).dump()
        else:
            src = args.get("--src", None)
            dest = args.get("--dest", None)

            if src and dest:
                src = LocationFactory(src, self)
                dest = LocationFactory(dest, self)

                dump = src.dump()
                dest.restore(dump)

                if assets:
                    src.copy_assets_to(dest)
