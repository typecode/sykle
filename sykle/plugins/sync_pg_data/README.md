# sync_pg_data

Wrapper around `pg_restore`, `pg_dump` and `psql` that allows you to sync data from one location to another.

### Usage Instructions

This command will sync BOTH data and the schema. This has a couple implications:

- You will need to ensure that the place you are syncing FROM has code that is either the SAME or is OLDER than the place you are syncing to. Although you **COULD** dump data from a newer codebase into data from an older codebase, if the database schema has changed, the code and migrations will not work properly.
  - `production -> staging` ✅
  - `staging -> development` ✅
  - `production -> development` ✅
  - ~~`staging -> production`~~ ❌
  - ~~`development -> staging`~~ ❌
  - ~~`development -> production`~~ ❌
- Any services using the destination database will need to be stopped. You can use the `dependent_services` section of the config to list docker-compose services that should automatically be stopped and restarted.
- Syncing will DELETE all data in the destination database and replace it with data from the source. You can make a backup before syncing using the `dump` command

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
