# sync_pg_data

Wrapper around `pg_restore`, `pg_dump` and `psql` that allows you to sync data from one location to another.

### Data only

This command does NOT do a full database dump and restore. Dumps and restores DATA ONLY so we can sync apps that still have active connections. This means all tables in the source that you would like to link to the destination must be present.

### Truncation

In order to avoid foreign key constraint errors when restoring data, any existing data must be removed. This means *THE ORIGINAL DESTINATION DATA WILL BE REMOVED*.

### Why put this in syk?

- Using `pg_dump` and `psql` without an alias is annoying
- Central location allows us to switch sync strategies across multiple projects if there's a better tool/a problem with pg_dump/psql
- New projects that use syk get a db sync tool for free
- Can point to same env vars in sync command as are used when deployed

### Requirements

- `pg_restore` (tested with version 10.5)
- `pg_dump` (tested with version 10.5)
- `psql` (tested with version 10.5)

### Safety Features

Sometimes there are databases that you always want to read from and never sync data to (like production). In order to prevent users from accidentally overwriting databases, you must explicitly set the "write" property on a location configuration to true in order to copy data to that location

In addition, `sync_pg_data` will ask for confirmation before truncating/overwriting data

### Usage

Usage instructions can be viewed after installation with `sykle sync_pg_data --help`

```
Sync PG Data

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

```
