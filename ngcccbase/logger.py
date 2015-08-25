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
try:
    from restapi_logging_handler import RestApiHandler as BaseRestApiHandler
    log_over_http = True
except ImportError:
    log_over_http = False
    BaseRestApiHandler = object

DEBUG_LEVEL = os.environ.get('NGCCC_DEBUG_LEVEL', False)
DEBUG_SERVER_PORT = os.environ.get('NGCCC_DEBUG_SERVER_PORT', 20520)
LOG_TO_TERMINAL = os.environ.get('NGCCC_LOG_TO_TERMINAL', False)

level_by_name = {}
for level in (10, 20, 30, 40, 50):
    level_by_name[logging.getLevelName(level)] = level


class RestApiHandler(BaseRestApiHandler):

    def setName(self, name='RestApiHandler'):
        self.name = name

    def _getPayload(self, record):

        payload = {
            'log': record.name,
            'level': logging.getLevelName(record.levelno),
            'message': self.format(record)  # Apply the formatter to records before sending them.
        }
        tb = self._getTraceback(record)
        if tb:
            payload['traceback'] = tb
        return payload


def setup_logging():

    logger = logging.getLogger('ngcccbase')
    if log_over_http and not LOG_TO_TERMINAL:
        endpoint = 'http://localhost:%s/endpoint' % DEBUG_SERVER_PORT
        fh = RestApiHandler(endpoint)
        fh.setName("Logging with RestApiHandler to '%s' (pid %s)" % (endpoint, os.getpid()))
    else:
        fh = logging.StreamHandler()
        fh.setName("Logging with StreamHandler (pid %s)" % (os.getpid(), ))
    if DEBUG_LEVEL in (level_by_name.keys()):
        logger.setLevel(level_by_name[DEBUG_LEVEL])
        formatter = logging.Formatter(  # Verbose format for filtering with e.g. grep
            '%(module)s:%(funcName)s:%(lineno)d: - "%(message)s" [%(threadName)s pid%(process)d- LogLevel%(levelno)s - %(levelname)s ] %(asctime)s')
        fh.setFormatter(formatter)
    else:
        logger.setLevel(logging.CRITICAL)

    if not fh.name in [h.name for h in logger.handlers]:
        logger.addHandler(fh)
        print fh.name
