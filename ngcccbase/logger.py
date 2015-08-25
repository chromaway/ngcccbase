# Logger module. Logs over http (if RestApiHandler is available),
# to avoid race conditions between threads or processes.
#
# The NGCCC_LOG_TO_TERMINAL env variable disables
# RestApiHandler.
#
# NGCCC_DEBUG_LEVEL env should be set for debugging, e.g. to 'DEBUG'
# It defaults to 'CRITICAL', so end users aren't spammed with messages.
# If set, it also formats log messages verbosely,
# for further filtering and analysis.
#
# NGCCC_DEBUG_SERVER_PORT changes what port
# the http logger logs to (a matching receiving server is in the
# tests directory).

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
    def setName(self, name='RestApiHandler'):
        self.name = name
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

