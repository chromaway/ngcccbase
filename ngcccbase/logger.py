import logging
import logging.handlers
import os
develop_mode = True
try:
    from restapi_logging_handler import RestApiHandler as BaseRestApiHandler
except ImportError:
    develop_mode = False
    BaseRestApiHandler = object


class RestApiHandler(BaseRestApiHandler):
    def _getPayload(self, record):
        """
        The data that will be sent to the RESTful API
        """
        payload = {
            'log': record.name,
            'level': logging.getLevelName(record.levelno),
            'message': self.format(record)
        }
        tb = self._getTraceback(record)
        if tb:
            payload['traceback'] = tb
        return payload

def setup_logging():
    logger = logging.getLogger('ngcccbase')
    formatter = logging.Formatter(
        '%(module)s:%(funcName)s:%(lineno)d: - "%(message)s" [%(threadName)s - LogLevel%(levelno)s - %(levelname)s ] %(asctime)s')
    logger.setLevel(logging.DEBUG)
    if develop_mode:
        fh = RestApiHandler('http://localhost:20520/endpoint')
    else:
        fh = logging.StreamHandler()
    fh.setFormatter(formatter)
    logger.addHandler(fh)

