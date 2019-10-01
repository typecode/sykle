import pkgutil
import sys
import sykle.plugins
import os
from distutils.version import LooseVersion

from .call_subprocess import call_subprocess


class PluginDir:
    def __init__(self, name, file_finder):
        self.name = name
        self.file_finder = file_finder

    @property
    def module(self):
        return self.file_finder.find_loader(self.name)[0]

    @property
    def path(self):
        return os.path.join(self.file_finder.path, self.name)

    @property
    def requirements_file(self):
        return os.path.join(self.path, 'requirements.txt')

    def install_requirements(self):
        if os.path.isfile(self.requirements_file):
            call_subprocess([
                sys.executable, '-m', 'pip', 'install',
                '-r', self.requirements_file
            ])


class Plugins():
    def __init__(self, config, sykle):
        self.config = config
        self.sykle = sykle
        self.plugins = Plugins.get_module_loaders()

    @staticmethod
    def list():
        return Plugins.get_module_loaders()

    @staticmethod
    def exists(name):
        return name in Plugins.get_module_loaders().keys()

    @staticmethod
    def get_module_loaders():
        plugins = {}
        plugin_path = sykle.plugins.__path__

        for file_finder, name, _ in pkgutil.iter_modules(plugin_path):
            plugins[name] = PluginDir(name, file_finder)

        plugins_path = os.path.join(os.getcwd(), '.syk-plugins')
        if os.path.isdir(plugins_path):
            for file_finder, name, _ in pkgutil.iter_modules([plugins_path]):
                if name in plugins:
                    print(
                        'WARNING: local "{}" plugin overwrites global plugin'
                        .format(name)
                    )
                plugins[name] = PluginDir(name, file_finder)
        return plugins

    def run(self, name):
        plugin_dir = self.plugins.get(name)
        plugin_module = plugin_dir.module.load_module()
        plugin = plugin_module.Plugin(
            config=self.config, sykle=self.sykle, dir=plugin_dir)
        plugin.run()


class IPlugin():
    def __init__(self, config, sykle, dir):
        if not self.NAME:
            raise Exception('Must give a plugin a NAME attribute!')

        self.sykle = sykle
        self.syk_config = config
        self.config = config.for_plugin(self.NAME)
        self._dir = dir
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

    @property
    def dir(self):
        return self._dir

    def run(self):
        raise NotImplementedError("Plugin needs a run method!")
