import sys
sys.path.append('../../../')
import logging.handlers
import os
from server_dist.server.common.variables import LOGGING_LEVEL

# создаём формировщик логов (formatter):
server_formatter = logging.Formatter('%(asctime)s %(levelname)s %(filename)s %(message)s')

# Подготовка имени файла для логирования
path = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(path, 'server.log')

log_file = logging.handlers.TimedRotatingFileHandler(path, encoding='utf8', interval=1, when='D')
log_file.setFormatter(server_formatter)

# создаём регистратор и настраиваем его
logger = logging.getLogger('server_dist')
logger.addHandler(log_file)
logger.setLevel(LOGGING_LEVEL)

# отладка
if __name__ == '__main__':
    logger.critical('Test critical event')
    logger.error('Test error ivent')
    logger.debug('Test debug ivent')
    logger.info('Test info ivent')
