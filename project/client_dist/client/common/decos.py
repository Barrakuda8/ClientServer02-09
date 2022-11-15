import sys
import logging
import socket

# метод определения модуля, источника запуска.
if sys.argv[0].find('client_dist') == -1:
    #если не клиент то сервер!
    logger = logging.getLogger('server_dist')
else:
    # ну, раз не сервер, то клиент
    logger = logging.getLogger('client_dist')


def log(func_to_log):
    """
    :param func_to_log: функция для декорирования
    Функция-декоратор, осуществляющая логирование других функций
    """

    def log_saver(*args, **kwargs):
        logger.debug(f'Была вызвана функция {func_to_log.__name__} c параметрами {args} , {kwargs}. Вызов из модуля {func_to_log.__module__}')
        ret = func_to_log(*args, **kwargs)
        return ret
    return log_saver