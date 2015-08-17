import logging
import logging.handlers
import os


def setup_logging():
    logger = logging.getLogger('ngcccbase')
    formatter = logging.Formatter('%(module)s:%(funcName)s:%(lineno)d: - "%(message)s" [%(threadName)s - LogLevel%(levelno)s - %(levelname)s ] %(asctime)s')
    logger.setLevel(logging.DEBUG)
    dir_path = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(dir_path, 'logs', 'ngcccbase.log')
    fh = logging.handlers.RotatingFileHandler(
              log_file, maxBytes=2000000, backupCount=1)
    sh = logging.StreamHandler()
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    # logger.addHandler(sh)
# 