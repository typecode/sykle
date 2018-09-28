# sync_s3

Uses `boto3` to copy data from s3 either locally or to another s3 bucket

### Usage

Usage instructions can be viewed after installation with `sykle sync_s3 --help`

```
Sync S3

Usage:
  syk sync_s3 --src=<bucket> --dest=<bucket> [--local-dir=<dir>] [--folder=<folder>] [--debug]

Options:
  -h --help             Show help info
  --version             Show version
  --src=<bucket>        Name of the bucket
  --dest=<bucket>       Specify where to push data to [default: local]
  --debug               Print debug information
  --local-dir=<dir>     Directory to use when copying to local [default: s3_dump]
  --folder=<dir>        Folder to sync

Example .sykle.json:
  {
     "plugins": {
        "sync_s3": {
            "access_key_id": "asdf",
            "secret_access_key": "asdf",
            "region_name": "asdf"
        }
     }
  }

```
