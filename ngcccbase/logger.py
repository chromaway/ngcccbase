import logging
import logging.handlers
import os


import multiprocessing_logging

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'ngcccbase.log')
mhandler = multiprocessing_logging.MultiProcessingHandler('worker-logger', sub_handler= logging.handlers.RotatingFileHandler(
              log_file, maxBytes=20000000, backupCount=0))

def setup_logging():
    logger = logging.getLogger('ngcccbase')
    logger.setLevel(logging.CRITICAL)
    formatter = logging.Formatter(  # Verbose format for filtering with e.g. grep
            '%(module)s:%(funcName)s:%(lineno)d: - "%(message)s" [%(threadName)s pid%(process)d- LogLevel%(levelno)s - %(levelname)s ] %(asctime)s')
    mhandler.setFormatter(formatter)
    mhandler.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.CRITICAL)
    logger.addHandler(mhandler)
    logger.addHandler(sh)
