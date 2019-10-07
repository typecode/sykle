"""bootstrap

Usage:
  syk bootstrap django <name> \
    [--apps=<apps>] \
    [--api-framework=<api_framework>] \
    [--cms-framework=<cms_framework>] \
    [--email-backend=<email_backend>] \
    [--error-logging=<error_logging] \
    [--storage-backend=<storage_backend>] \
    [--search-backend=<search_backend>] \
    [--task-queue=<task_queue]

Options:
  --apps=<apps>                         A comma-separated list of the apps to
                                        stub. Defaults to ["core"].
  --api-framework=<rest,graphql>        An API framework to install.
  --cms-framework=<wagtail>             A CMS framework to install.
  --email-backend=<ses>                 An email backend to install.
  --error-logging=<sentry>              An error logging service to install.
  --storage-backend=<s3>                A storage backend in which to store
                                        media and static files.
  --search-backend=<elasticsearch_dsl>  A backend for textual filtering.
  --task-queue=<celery>                 An backend for asynchronous tasks.
  -h --help                             Show this screen.

Description:
  django                                Create a django project.
"""

__version__ = '0.1.0'
import logging

from docopt import docopt

from sykle.plugin_utils import IPlugin

from .template_renderer import TemplateRenderer
from .utils import kebab_arg_to_snake_case


logger = logging.getLogger(__name__)


class Plugin(IPlugin):
    NAME = 'bootstrap'

    arg_extensions = [
        '--api-framework',
        '--cms-framework',
        '--email-backend',
        '--error-logging',
        '--storage-backend',
        '--search-backend',
        '--task-queue'
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.args = docopt(__doc__, version=__version__)

        extensions = Plugin.args_to_extensions(self.args)

        app_names = self.args.get('--apps') or 'core'
        app_names = app_names.split(',')

        self.renderer = TemplateRenderer(
            project_name=self.args['<name>'],
            base_dir=self.dir.path,
            extensions=extensions,
            app_names=app_names
        )

    @staticmethod
    def args_to_extensions(args):
        return [
            (kebab_arg_to_snake_case(k), v)
            for k, v in args.items()
            if k in Plugin.arg_extensions and v is not None
        ]

    def new_django_project(self):
        self.renderer.render()

    @logger.halo(succeed=True)
    def run(self):
        if self.args['django']:
            self.new_django_project()
