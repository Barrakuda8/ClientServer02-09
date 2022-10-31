import configparser
import os.path
import socket
import argparse
import select
from common.utils import *
from common.decos import log
from common.metaclasses import ServerVerifier
import threading
from server_db import ServerDB
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from server_gui import MainWindow, create_active_users_model, create_message_history_model, MessageHistoryWindow, ConfigWindow

logger = logging.getLogger('server_dist')

conflag_lock = threading.Lock()
new_connection = False


class PortDescriptor:
    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            logger.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {value}. Допустимы адреса с 1024 до 65535.')
            exit(1)
        instance.__dict__[self.name] = value


class Server(threading.Thread, metaclass=ServerVerifier):

    port = PortDescriptor()

    def __init__(self, address, port, db):
        super().__init__()
        self.daemon = True
        self.address = address
        self.port = port
        self.db = db

        self.clients = []
        self.messages = []
        self.names = {}
        self.receivers = []
        self.senders = []
        self.errors = []

    def process_client_message(self, message, client):
        global new_connection
        logger.debug(f'Разбор сообщения от клиента : {message}')
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.db.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
                with conflag_lock:
                    new_connection = True
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        elif ACTION in message and message[ACTION] == MESSAGE and RECEIVER in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message and self.names[message[SENDER]] == client:
            if message[RECEIVER] in self.names:
                self.messages.append(message)
                self.db.process_message(message[SENDER], message[RECEIVER])
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                send_message(client, response)
            return
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.db.user_logout(message[ACCOUNT_NAME])
            with conflag_lock:
                new_connection = True
            self.clients.remove(self.names[ACCOUNT_NAME])
            self.names[ACCOUNT_NAME].close()
            del self.names[ACCOUNT_NAME]
            return
        elif ACTION in message and message[ACTION] == GET_USERS and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[DATA] = [user[0] for user in self.db.get_users()]
            send_message(client, response)
        elif ACTION in message and message[ACTION] == GET_CONTACTS and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[DATA] = self.db.get_contacts(message[ACCOUNT_NAME])
            send_message(client, response)
        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.db.add_contact(message[ACCOUNT_NAME], message[CONTACT])
            send_message(client, RESPONSE_200)
        elif ACTION in message and message[ACTION] == DEL_CONTACT and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.db.delete_contact(message[ACCOUNT_NAME], message[CONTACT])
            send_message(client, RESPONSE_200)
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return

    def process_message(self, message):
        if message[RECEIVER] in self.names and self.names[message[RECEIVER]] in self.receivers:
            send_message(self.names[message[RECEIVER]], message)
            logger.info(f'Отправлено сообщение пользователю {message[RECEIVER]} от пользователя {message[SENDER]}.')
        elif message[RECEIVER] in self.names and self.names[message[RECEIVER]] not in self.receivers:
            raise ConnectionError
        else:
            logger.error(
                f'Пользователь {message[RECEIVER]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    def run(self):
        global new_connection
        logger.info(
            f'Запущен сервер, порт для подключений: {self.port} , '
            f'адрес с которого принимаются подключения: {self.address}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.address, self.port))
        transport.settimeout(0.5)

        transport.listen()
        while True:
            try:
                client, client_address = transport.accept()
            except OSError:
                pass
            else:
                logger.info(f'Установлено соедение с ПК {client_address}')
                self.clients.append(client)

            try:
                if self.clients:
                    self.senders, self.receivers, self.errors = select.select(self.clients, self.clients, [], 0)
            except OSError as e:
                self.senders = []
                self.receivers = []
                self.errors = []
                logger.error(f'Ошибка работы с сокетами: {e}')

            if self.senders:
                for client_with_message in self.senders:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except OSError as e:
                        print(e)
                        logger.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        for name in self.names:
                            if self.names[name] == client_with_message:
                                self.db.user_logout(name)
                                del self.names[name]
                                break
                        self.clients.remove(client_with_message)
                        with conflag_lock:
                            new_connection = True

            for message in self.messages:
                try:
                    self.process_message(message)
                except Exception as e:
                    print(e)
                    logger.info(f'Связь с клиентом с именем {message[RECEIVER]} была потеряна')
                    self.clients.remove(self.names[message[RECEIVER]])
                    self.db.user_logout(message[RECEIVER])
                    del self.names[message[RECEIVER]]
                    with conflag_lock:
                        new_connection = True
            self.messages.clear()


@log
def arg_parser(default_port, default_address):
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    return listen_address, listen_port


def main():
    config = configparser.ConfigParser()
    config.read(f"{os.path.dirname(os.path.realpath(__file__))}/{'server.ini'}")
    listen_address, listen_port = arg_parser(config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_address'])
    db = ServerDB(os.path.join(config['SETTINGS']['Database_path'], config['SETTINGS']['Database_file']))

    server = Server(listen_address, listen_port, db)
    server.start()

    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    main_window.statusBar().showMessage('Сервер работает')
    main_window.active_clients_table.setModel(create_active_users_model(db))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    def active_clients_renew():
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(create_active_users_model(db))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    def show_message_history():
        global message_history_window
        message_history_window = MessageHistoryWindow()
        message_history_window.message_history_table.setModel(create_message_history_model(db))
        message_history_window.message_history_table.resizeColumnsToContents()
        message_history_window.message_history_table.resizeRowsToContents()
        message_history_window.show()

    def server_config():
        global config_window
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_address'])
        config_window.save_button.clicked.connect(save_server_config)

    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['Listen_address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                with open('server.ini', 'w') as conf:
                    conf.write(config)
                    message.information(config_window, 'ОК', 'Настройки успешно сохранены!')
            else:
                message.warning(config_window, 'Ошибка', 'Порт должен быть от 1024 до 65535')

    timer = QTimer()
    timer.timeout.connect(active_clients_renew)
    timer.start(1000)

    main_window.refresh_button.triggered.connect(active_clients_renew)
    main_window.show_message_history_button.triggered.connect(show_message_history)
    main_window.config_button.triggered.connect(server_config)

    server_app.exec_()


if __name__ == '__main__':
    main()
