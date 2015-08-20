import logging
import logging.handlers
import os
import cloghandler

def setup_logging():
    logger = logging.getLogger('ngcccbase')
    # formatter = logging.Formatter(
    #     '%(module)s:%(funcName)s:%(lineno)d: - "%(message)s" [%(threadName)s - LogLevel%(levelno)s - %(levelname)s ] %(asctime)s')
    # logger.setLevel(logging.DEBUG)
    # dir_path = os.path.dirname(os.path.abspath(__file__))
    # log_file = os.path.join(dir_path, 'logs', 'ngcccbase.log')
    # fh = cloghandler.ConcurrentRotatingFileHandler(
    #           log_file, maxBytes=2000000, backupCount=1)
    # fh.setFormatter(formatter)
    # logger.addHandler(fh)
