from sykle.cli import __doc__
from sykle.plugin_utils import Plugins
from sykle.config import Config
import os
import chevron

PLUGINS_PATH = os.path.join(os.path.dirname(__file__), 'sykle.plugins')
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'README.mustache')
README_PATH = os.path.join(os.path.dirname(__file__), 'README.md')


def create_readme(template, destination, docstring):
    if not os.path.isfile(template):
        return

    long_description = None
    with open(template, 'r', encoding='utf-8') as f:
        long_description = chevron.render(f.read(), {
            'usage': docstring,
            'config_example': Config.CONFIG_FILE_EXAMPLE,
        })

    if os.path.isfile(destination):
        os.chmod(destination, 0o644)
    with open(destination, 'w+', encoding='utf-8') as f:
        f.write(long_description)

    os.chmod(destination, 0o400)


create_readme(TEMPLATE_PATH, README_PATH, __doc__)

for plugin in Plugins.list():
    doc = Plugins.load(plugin).__doc__
    template = os.path.join(PLUGINS_PATH, plugin, 'README.mustache')
    destination = os.path.join(PLUGINS_PATH, plugin, 'README.md')
    create_readme(template, destination, doc)
