# sync_pg_data

Wrapper around `pg_dump` and `psql` that allows you to sync data from one location to another

### Why put this in syk?

- Using `pg_dump` and `psql` without an alias is annoying
- Central location allows us to switch sync strategies across multiple projects if there's a better tool/a problem with pg_dump/psql
- New projects that use syk get a db sync tool for free
- Can point to same env vars in sync command as are used when deployed

### Requirements

- `pgdump`
- `psql`

### Usage

Usage instructions can be viewed after installation with `sykle sync_pg_data --help`

```
Sync PG Data

Usage:
  syk sync_pg_data [--src=<name>] [--dest=<name>] [--debug]

Options:
  -h --help         Show help info
  --version         Show version
  --src=<name>      Specify where to pull data from [default: staging]
  --dest=<name>     Specify where to push data to [default: local]
  --debug           Print debug information

Example .sykle.json:
  {
     "plugins": {
        "sync_pg_data": {
            "local": {               // Name of location
               "PORT": 5432,         // Port for postgres (OPTIONAL)
               "HOST": "localhost",  // Host for postgres
               "USER": "postgres",   // Username for postgres
               "PASSWORD": "asdf"    // Password for postgres
            }
        }
     }
  }

```
