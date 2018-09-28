"""Sync S3

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
"""

__version__ = '0.0.1'

from src.plugins import IPlugin
from src.config import Config
from docopt import docopt
import os
import boto3
import shutil
import errno


class Plugin(IPlugin):
    REQUIRED_ARGS = ['access_key_id', 'secret_access_key', 'region_name']
    name = 'sync_s3'

    def run(self):
        args = docopt(__doc__, version=__version__)

        for k in Plugin.REQUIRED_ARGS:
            if k not in self.config:
                raise Exception('sync_s3 config missing "{}" arg!'.format(k))

        self.create_session()
        self.s3 = boto3.resource('s3')

        self.folder = args['--folder']
        self.local_dir = args['--local-dir']

        self.src_bucket_name = args['--src']
        self.src_bucket = self.s3.Bucket(args['--src'])

        if args['--dest'] == 'local':
            self.s3_to_local()
        else:
            self.dest_bucket_name = args['--dest']
            self.dest_bucket = self.s3.Bucket(args['--dest'])
            self.s3_to_s3()

    def create_session(self):
        config = self.config
        env_file = config.get('env_file')
        if env_file:
            config = Config.interpolate_env_values_from_file(config, env_file)

        boto3.Session(aws_access_key_id=config['access_key_id'],
                      aws_secret_access_key=config['secret_access_key'],
                      region_name=config['region_name'])

    def copy_tree(self, client, resource, loc, dest, bucket=None, out=''):
        paginator = client.get_paginator('list_objects')
        for result in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix=loc):
            if result.get('CommonPrefixes') is not None:
                for subdir in result.get('CommonPrefixes'):
                    out = self.copy_tree(client, resource, subdir.get('Prefix'), dest, bucket, out)
            if result.get('Contents') is not None:
                for file in result.get('Contents'):
                    key = file.get('Key')
                    local_filename = '/'.join(key.split('/')[1:])
                    local_path = os.path.join(dest, local_filename)
                    if not os.path.exists(os.path.dirname(local_path)):
                        os.makedirs(os.path.dirname(local_path))
                    resource.meta.client.download_file(bucket, key, local_path)
                    out += 'copied {}\n'.format(local_path)
        return out

    def s3_to_s3(self):
        out, err = '\n', None
        for obj in self.dest_bucket.objects.filter(Prefix=self.folder):
            out += 'deleted {}\n'.format(obj.key)
            obj.delete()

        out += '\n'

        for obj in self.src_bucket.objects.filter(Prefix=self.folder):
            self.s3.meta.client.copy(
                {
                    'Bucket': self.src_bucket_name,
                    'Key': obj.key
                },
                self.dest_bucket_name,
                obj.key
            )
            out += 'copied {}\n'.format(obj.key)

        return out, err

    def mkdirp(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def s3_to_local(self):
        local_dir = os.path.join(self.local_dir, self.folder)
        self.mkdirp(self.local_dir)

        for (dirpath, dirnames, filenames) in os.walk(local_dir):
            for file in filenames:
                os.remove(os.path.join(dirpath, file))
            for directory in dirnames:
                shutil.rmtree(os.path.join(dirpath, directory))

        client = boto3.client('s3')
        out = '\n{}'.format(self.copy_tree(client, self.s3, self.folder,
                            self.local_dir, self.src_bucket_name))

        return out, None
