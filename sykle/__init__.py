import logging
from .logger import FancyLogger
from .sykle import Sykle


__version__ = Sykle.version

logging.setLoggerClass(FancyLogger)
logging.basicConfig(level=logging.INFO)
