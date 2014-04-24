import logging

def setup_logging():
    logger = logging.getLogger('ngcccbase')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
