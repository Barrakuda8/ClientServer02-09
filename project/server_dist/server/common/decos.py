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


def login_required(func):
    """
    :param func: функция для декорирования
    Функция-декоратор, проверяющая залогинен ли клиент на сервере
    """

    def checker(*args, **kwargs):
        from server_files.core import MessageProcessor
        from common.variables import ACTION, PRESENCE
        if isinstance(args[0], MessageProcessor):
            found = False
            for arg in args:
                if isinstance(arg, socket.socket):
                    for client in args[0].names:
                        if args[0].names[client] == arg:
                            found = True

            for arg in args:
                if isinstance(arg, dict):
                    if ACTION in arg and arg[ACTION] == PRESENCE:
                        found = True
            if not found:
                raise TypeError
        return func(*args, **kwargs)

    return checker