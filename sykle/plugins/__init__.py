import logging
from sykle.logger import FancyLogger

logging.setLoggerClass(FancyLogger)
logging.basicConfig(level=logging.INFO)
