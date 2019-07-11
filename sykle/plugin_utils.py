import pkgutil
import sykle.plugins
import os
from distutils.version import LooseVersion


class Plugins():
    def __init__(self, config, sykle):
        self.config = config
        self.sykle = sykle
        self.plugins = Plugins.get_module_loaders()

    @staticmethod
    def load(name):
        return Plugins.get_module_loaders().get(name).load_module()

    @staticmethod
    def list():
        return Plugins.get_module_loaders().keys()

    @staticmethod
    def get_module_loaders():
        plugins = {}
        plugin_path = sykle.plugins.__path__

        for file_finder, name, _ in pkgutil.iter_modules(plugin_path):
            plugins[name] = file_finder.find_loader(name)[0]

        plugins_path = os.path.join(os.getcwd(), '.syk-plugins')
        if os.path.isdir(plugins_path):
            for file_finder, name, _ in pkgutil.iter_modules([plugins_path]):
                if name in plugins:
                    print(
                        'WARNING: local "{}" plugin overwrites global plugin'
                        .format(name)
                    )
                plugins[name] = file_finder.find_loader(name)[0]
        return plugins

    @staticmethod
    def exists(name):
        return name in Plugins.get_module_loaders()

    def run(self, name):
        self.load(name).Plugin(config=self.config, sykle=self.sykle).run()


class IPlugin():
    def __init__(self, config, sykle):
        if not self.NAME:
            raise Exception('Must give plugin a name! (via name attribute)')

        self.sykle = sykle
        self.syk_config = config
        self.config = config.for_plugin(self.NAME)
        self._check_compatibility()

    def _check_compatibility(self):
        required_version = getattr(self, 'REQUIRED_VERSION', None)
        current_version = self.sykle.version
        if (
            required_version and
            (LooseVersion(required_version) > LooseVersion(current_version))
        ):
            raise Exception(
                'Plugin requires sykle {} (using version {})'
                .format(required_version, current_version)
            )

    def run(self):
        raise NotImplementedError("Plugin needs a run method!")
