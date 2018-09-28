import importlib
import os


class Plugins():
    def __init__(self, config):
        self.config = config

    @staticmethod
    def load(name):
        return importlib.import_module('plugins.{}'.format(name))

    @staticmethod
    def list():
        return os.listdir(os.path.join(os.path.dirname(__file__), '../plugins'))

    @staticmethod
    def exists(name):
        try:
            Plugins.load(name)
            return True
        except ImportError:
            return False

    def run(self, name):
        self.load(name).Plugin(config=self.config).run()


class IPlugin():
    def __init__(self, config):
        self.syk_config = config
        self.config = config.for_plugin(self.name)

    def run(self):
        raise NotImplemented("Plugin needs a run method!")
