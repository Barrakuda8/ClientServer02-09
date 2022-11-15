import argparse
import os
import logging
from Cryptodome.PublicKey import RSA
from PyQt5.QtWidgets import QApplication, QMessageBox
from client_files.main_window import ClientMainWindow
from client_files.start_dialog import UserNameDialog
from client_files.transport import ClientTransport
from common.errors import ServerError
from common.decos import log
from client_files.client_db import ClientDB

logger = logging.getLogger('client_dist')


@log
def arg_parser():
    """
    Метод, разбирающий команду и вытаскивающий из неё параметры
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    address = namespace.addr
    port = namespace.port
    name = namespace.name
    password = namespace.password

    if not 1023 < port < 65536:
        logger.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {port}. '
            f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
        exit(1)

    return address, port, name, password


if __name__ == '__main__':
    server_address, server_port, client_name, client_password = arg_parser()

    client_app = QApplication(sys.argv)

    start_dialog = UserNameDialog()
    if not client_name or not client_password:
        client_app.exec_()
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_password = start_dialog.client_password.text()
            logger.debug(f'Using USERNAME = {client_name}, PASSWD = {client_password}.')
        else:
            exit(0)

    key_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), f'{client_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())

    logger.debug("Keys successfully loaded.")

    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , '
        f'порт: {server_port}, имя пользователя: {client_name}')

    db = ClientDB(client_name)

    try:
        transport = ClientTransport(server_port, server_address, client_name, db, client_password, keys)
    except ServerError as error:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера', error.text)
        exit(1)
    transport.start()

    del start_dialog

    main_window = ClientMainWindow(transport, db, keys)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат Программа alpha release - {client_name}')
    client_app.exec_()

    transport.transport_shutdown()
    transport.join()
