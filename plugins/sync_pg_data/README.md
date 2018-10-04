# sync_pg_data

Wrapper around `pg_dump` and `psql` that allows you to sync data from one location to another

### Why put this in syk?

- Using `pg_dump` and `psql` without an alias is annoying
- Central location allows us to switch sync strategies across multiple projects if there's a better tool/a problem with pg_dump/psql
- New projects that use syk get a db sync tool for free
- Can point to same env vars in sync command as are used when deployed

### Requirements

- `pg_dump` (tested with version 10.5)
- `psql` (tested with version 10.5)

### Safety Features

Sometimes there are databases that you always want to read from and never sync data to (like production). In order to prevent users from accidentally overwriting databases, you must explicitly set the "write" property on a location configuration to true in order to copy data to that location

### Usage

Usage instructions can be viewed after installation with `sykle sync_pg_data --help`

```
Sync PG Data

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

```