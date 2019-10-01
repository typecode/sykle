import logging

from contextlib import contextmanager

from halo import Halo
from termcolor import colored


def red(string):
    return colored(string, 'red')


def yellow(string):
    return colored(string, 'yellow')


def green(string):
    return colored(string, 'green')


class HaloHandler(logging.StreamHandler):
    """A logging handler that emits log records to a halo
    stream if it exists.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._halo = None

    @property
    def halo(self):
        return self._halo

    @halo.setter
    def halo(self, halo):
        self._halo = halo

    def releaseHalo(self):
        self._halo = None

    def emit(self, record):
        if self.halo:
            self.halo.text = self.format(record)
        else:
            super().emit(record)


DEFAULT_HALO_SPINNER = 'dots9'
DEFAULT_HALO_PLACEMENT = 'left'


class FancyLogger(logging.Logger):
    """A Logger with text embellishment and command line spinners.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.propagate = False

        self.haloHandler = HaloHandler()
        self.addHandler(self.haloHandler)

    @contextmanager
    def halo(
        self,
        succeed=False,
        spinner=DEFAULT_HALO_SPINNER,
        placement=DEFAULT_HALO_PLACEMENT,
        **kwargs
    ):
        """Method for (a) managing the context of or (b) decorating a
        function with a halo whose stream is that of this logger's
        handler. Messages logged to this logger within the decorated
        function or context will appear and disappear next to the halo
        spinner.
        """
        halo = Halo(spinner=spinner, placement=placement, **kwargs)
        self.haloHandler.halo = halo

        try:
            halo.start()
            yield halo
            if succeed:
                halo.succeed(green('Success!'))
        finally:
            halo.stop()

            self.haloHandler.releaseHalo()

    def warn(self, msg):
        super().warn(yellow(msg))

    def error(self, msg):
        super().error(red(msg))

    def exception(self, msg):
        super().exception(red(msg))

    def critical(self, msg):
        super().critical(red(msg))

    def info(self, msg):
        super().info(green(msg))
