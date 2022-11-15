import threading
import select
import socket
import json
import hmac
import binascii
import os
import sys
import logging
from common.utils import send_message, get_message
from common.decos import login_required
from common.variables import *

logger = logging.getLogger('server_dist')


class PortDescriptor:
    """
    Дескриптор, проверяющий, чтобы значение введённого порта было от 1024 до 65535
    """

    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            logger.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {value}. Допустимы адреса с 1024 до 65535.')
            exit(1)
        instance.__dict__[self.name] = value


class MessageProcessor(threading.Thread):
    """
    Класс, реализующий функционал сервера
    """

    port = PortDescriptor()

    def __init__(self, address, port, db):
        super().__init__()
        self.daemon = True
        self.address = address
        self.port = port
        self.db = db
        self.transport = None

        self.clients = []
        self.messages = []
        self.names = {}
        self.receivers = None
        self.errors = None

        self.running = True

    def run(self):
        """
        Метод, запускающий сервер и реализующий функционал приёма и передачи сообщений
        """

        logger.info(
            f'Запущен сервер, порт для подключений: {self.port} , '
            f'адрес с которого принимаются подключения: {self.address}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.transport.bind((self.address, self.port))
        self.transport.settimeout(0.5)

        self.transport.listen()
        while self.running:
            try:
                client, client_address = self.transport.accept()
            except OSError:
                pass
            else:
                logger.info(f'Установлено соедение с ПК {client_address}')
                client.settimeout(5)
                self.clients.append(client)

            senders = []

            try:
                if self.clients:
                    senders, self.receivers, self.errors = select.select(self.clients, self.clients, [], 0)
            except OSError as e:
                logger.error(f'Ошибка работы с сокетами: {e}')

            if senders:
                for client_with_message in senders:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except (OSError, json.JSONDecodeError, TypeError) as err:
                        logger.debug(f'Getting data from client exception.', exc_info=err)
                        self.delete_client(client_with_message)

    def delete_client(self, client):
        """
        :param client: сокет клиента

        Метод, отключающий клиента от сервера и удаляющий его из словаря текущих клиентов
        """

        logger.info(f'Клиент {client.getpeername()} отключился от сервера.')
        for name in self.names:
            if self.names[name] == client:
                self.db.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

    def process_message(self, message):
        """
        :param message: словарь, содержащий данные об обрабатываемом сообщении

        Метод, обеспечивающий отправление сообщения получателю, если он зарегистрирован на сервере
        """

        if message[RECEIVER] in self.names and self.names[message[RECEIVER]] in self.receivers:
            try:
                send_message(self.names[message[RECEIVER]], message)
                logger.info(f'Отправлено сообщение пользователю {message[RECEIVER]} от пользователя {message[SENDER]}.')
            except OSError:
                self.delete_client(message[RECEIVER])
        elif message[RECEIVER] in self.names and self.names[message[RECEIVER]] not in self.receivers:
            logger.error(f'Связь с клиентом {message[RECEIVER]} была потеряна. Соединение закрыто, доставка невозможна.')
            self.delete_client(self.names[message[RECEIVER]])
        else:
            logger.error(
                f'Пользователь {message[RECEIVER]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    @login_required
    def process_client_message(self, message, client):
        """
        :param message: словарь, содержащий данные об обрабатываемом сообщении
        :param client:  сокет клиента

        Метод, обрабатывающий сообщения  с командами от пользователя:
            -приветственное сообщение
            -сообщения другим пользователям
            -выход из программы
            -получение списка контактов пользователя
            -добавление контакта пользователя
            -удаление контакта пользователя
            -получение списка доступных пользователей
            -получение публичного ключа пользователя
        """

        logger.debug(f'Разбор сообщения от клиента : {message}')
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            self.autorize_user(message, client)

        elif ACTION in message and message[ACTION] == MESSAGE and RECEIVER in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message and self.names[message[SENDER]] == client:
            if message[RECEIVER] in self.names:
                self.db.process_message(
                    message[SENDER], message[RECEIVER])
                self.process_message(message)
                try:
                    send_message(client, RESPONSE_200)
                except OSError:
                    self.delete_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                try:
                    send_message(client, response)
                except OSError:
                    pass
            return
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.delete_client(client)
        elif ACTION in message and message[ACTION] == GET_CONTACTS and ACCOUNT_NAME in message and \
                self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[DATA] = self.db.get_contacts(message[ACCOUNT_NAME])
            try:
                send_message(client, response)
            except OSError:
                self.delete_client(client)
        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and CONTACT in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.db.add_contact(message[ACCOUNT_NAME], message[CONTACT])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.delete_client(client)
        elif ACTION in message and message[ACTION] == DEL_CONTACT and ACCOUNT_NAME in message and CONTACT in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.db.delete_contact(message[ACCOUNT_NAME], message[CONTACT])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.delete_client(client)
        elif ACTION in message and message[ACTION] == GET_USERS and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[DATA] = [user[0] for user in self.db.get_users()]
            try:
                send_message(client, response)
            except OSError:
                self.delete_client(client)
        elif ACTION in message and message[ACTION] == GET_PUBLIC_KEY and ACCOUNT_NAME in message:
            response = RESPONSE_511
            response[BIN] = self.db.get_public_key(message[ACCOUNT_NAME])
            if response[BIN]:
                try:
                    send_message(client, response)
                except OSError:
                    self.delete_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Нет публичного ключа для данного пользователя'
                try:
                    send_message(client, response)
                except OSError:
                    self.delete_client(client)
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            try:
                send_message(client, response)
            except OSError:
                self.delete_client(client)

    def autorize_user(self, message, transport):
        """
        :param message: словарь, содержащий данные об обрабатываемом сообщении
        :param transport: сокет клиента

        Метод, отвечающий за авторизацию пользователя на сервере. Проверяет не подключён ли уже пользователь к серверу и
        зарегистрирован ли на сервере, затем через алгоритм хэширования проверяет введённый пароль и осуществляет
        подключение пользователя, если всё в порядке
        """

        logger.debug(f'Start auth process for {message[USER]}')
        if message[USER][ACCOUNT_NAME] in self.names.keys():
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            try:
                logger.debug(f'Username busy, sending {response}')
                send_message(transport, response)
            except OSError:
                logger.debug('OS Error')
                pass
            self.clients.remove(transport)
            transport.close()
        elif not self.db.check_user(message[USER][ACCOUNT_NAME]):
            response = RESPONSE_400
            response[ERROR] = 'Пользователь не зарегистрирован.'
            try:
                logger.debug(f'Unknown username, sending {response}')
                send_message(transport, response)
            except OSError:
                pass
            self.clients.remove(transport)
            transport.close()
        else:
            logger.debug('Correct username, starting passwd check.')
            message_auth = RESPONSE_511
            random_str = binascii.hexlify(os.urandom(64))
            message_auth[BIN] = random_str.decode('ascii')
            hash = hmac.new(self.db.get_hash(message[USER][ACCOUNT_NAME]), random_str, 'MD5').digest()
            logger.debug(f'Auth message = {message_auth}')
            try:
                send_message(transport, message_auth)
                response = get_message(transport)
            except OSError as err:
                logger.debug('Error in auth, data:', exc_info=err)
                transport.close()
                return
            client_digest = binascii.a2b_base64(response[BIN])
            if RESPONSE in response and response[RESPONSE] == 511 and \
                    hmac.compare_digest(hash, client_digest):
                self.names[message[USER][ACCOUNT_NAME]] = transport
                client_ip, client_port = transport.getpeername()
                try:
                    send_message(transport, RESPONSE_200)
                except OSError:
                    self.delete_client(message[USER][ACCOUNT_NAME])
                self.db.user_login(
                    message[USER][ACCOUNT_NAME],
                    client_ip,
                    client_port,
                    message[USER][PUBLIC_KEY])
            else:
                response = RESPONSE_400
                response[ERROR] = 'Неверный пароль.'
                try:
                    send_message(transport, response)
                except OSError:
                    pass
                self.clients.remove(transport)
                transport.close()

    def service_update_lists(self):
        """
        Метод, осуществляющий обновление словаря пользователей сервера
        """

        for client in self.names:
            try:
                send_message(self.names[client], RESPONSE_205)
            except OSError:
                self.delete_client(self.names[client])
