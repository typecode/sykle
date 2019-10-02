"""Repo

Usage:
  syk scm new-repo <name> (--token=<token>) [--org=<org>]

Options:
  --org=<org>       A github organization [default: typecode].
  --token=<token>   A personal access token from github with repo permissions
                    for the org.
  -h --help         Show this screen.

Description:
  new-repo          Create a new github repo and clone it into the cwd.
"""

__version__ = '0.1.0'

import logging

from docopt import docopt

from sykle.plugin_utils import IPlugin

from .scm import SCM


logger = logging.getLogger(__name__)


class Plugin(IPlugin):
    NAME = 'repo'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.args = docopt(__doc__, version=__version__)

        self.scm = SCM(
            org=self.args.get('--org'),
            token=self.args.get('--token'),
        )

    def new_repo(self):
        repo_name = self.args['<name>']

        logger.info('Creating the repo')
        self.scm.create_repo(repo_name)

        logger.info('Creating a default development branch')
        self.scm.create_default_development_branch()

        logger.info('Adding the default team to the repo')
        self.scm.add_default_teams_to_repo()

        logger.info('Setting branch protections')
        self.scm.create_branch_protections()

        logger.info('Creating webhooks')
        self.scm.create_webhooks()

        logger.info('Cloning into the current directory')
        self.scm.clone_repo()

    @logger.halo(succeed=True)
    def run(self):
        if self.args['new-repo']:
            self.new_repo()
