import socket
import sys
import argparse
import json
import logging
import select
import time
import logs.config_server_log
from errors import IncorrectDataRecivedError
from common.variables import *
from common.utils import *
from decos import log
from metaclasses import ServerVerifier
import threading
from pprint import pprint
from server_db import ServerDB

logger = logging.getLogger('server_dist')


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
        logger.debug(f'Разбор сообщения от клиента : {message}')
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.db.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        elif ACTION in message and message[ACTION] == MESSAGE and RECEIVER in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.db.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[ACCOUNT_NAME])
            self.names[ACCOUNT_NAME].close()
            del self.names[ACCOUNT_NAME]
            return
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
        logger.info(
            f'Запущен сервер, порт для подключений: {self.port} , '
            f'адрес с которого принимаются подключения: {self.address}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.address, self.port))
        transport.settimeout(0.5)

        transport.listen(MAX_CONNECTIONS)
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
            except OSError:
                self.senders = []
                self.receivers = []
                self.errors = []

            if self.senders:
                for client_with_message in self.senders:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except Exception as e:
                        print(e)
                        logger.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        self.clients.remove(client_with_message)

            for message in self.messages:
                try:
                    self.process_message(message)
                except Exception as e:
                    print(e)
                    logger.info(f'Связь с клиентом с именем {message[RECEIVER]} была потеряна')
                    self.clients.remove(self.names[message[RECEIVER]])
                    del self.names[message[RECEIVER]]
            self.messages.clear()


class ServerConsole(threading.Thread):

    port = PortDescriptor()

    def __init__(self, db):
        super().__init__()
        self.daemon = True
        self.db = db

    def run(self):
        self.print_help()
        while True:
            option = input('Введите команду: ')
            if option == 'users':
                pprint(self.db.get_users())
            elif option == 'active':
                pprint(self.db.get_active_users())
            elif option.startswith('history '):
                user = ' '.join(option.split()[1:])
                try:
                    pprint(self.db.get_login_history(user))
                except:
                    print(f'Пользователя "{user}" не существует.')
            elif option == 'help':
                self.print_help()
            elif option == 'exit':
                print('До свидания!')
                logger.info('Завершения работы сервера по команде администратора.')
                time.sleep(2)
                exit(0)
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    @staticmethod
    def print_help():
        print('Поддерживаемые команды:')
        print('users - вывести список всех пользователей.')
        print('active - вывести список активных пользователей.')
        print('history [имя пользователя] - вывести историю входов конкретного пользователя.')
        print('help - вывести подсказки по командам')
        print('exit - завершение работы сервера')


@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    return listen_address, listen_port


def main():
    listen_address, listen_port = arg_parser()
    db = ServerDB()
    server = Server(listen_address, listen_port, db)
    console = ServerConsole(db)
    server.start()
    console.start()

    while True:
        time.sleep(1)
        if server.is_alive() and console.is_alive():
            continue
        break


if __name__ == '__main__':
    main()
