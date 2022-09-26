import datetime
import sys
import json
import socket
import time
import argparse
import logging
import threading
import logs.config_client_log
from common.variables import *
from common.utils import *
from errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError
from decos import log
from metaclasses import ClientVerifier
from pprint import pprint
from client_db import ClientDB

logger = logging.getLogger('client_dist')

db_lock = threading.Lock()
transport_lock = threading.Lock()


class Receiver(threading.Thread, metaclass=ClientVerifier):

    def __init__(self, transport, name, db):
        super().__init__()
        self.daemon = True
        self.transport = transport
        self.name = name
        self.db = db

    def run(self):
        while True:
            time.sleep(1)
            with transport_lock:
                try:
                    message = get_message(self.transport)
                except IncorrectDataRecivedError:
                    logger.error(f'Не удалось декодировать полученное сообщение')
                except OSError as err:
                    if err.errno:
                        logger.critical(f'Потеряно соединение с сервером.')
                        break
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError):
                    logger.critical(f'Потеряно соединение с сервером')
                    break
                else:
                    if ACTION in message and message[ACTION] == MESSAGE and \
                            SENDER in message and MESSAGE_TEXT in message and RECEIVER in message \
                            and message[RECEIVER] == self.name:
                        with db_lock:
                            try:
                                self.db.save_message(message[SENDER], self.name, message[MESSAGE_TEXT])
                            except:
                                logger.error('Ошибка взаимодействия с базой данных')
                        logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                        print(f'Получено сообщение от пользователя '
                              f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    else:
                        logger.error(f'Получено некорректное сообщение с сервера: {message}')


class Sender(threading.Thread, metaclass=ClientVerifier):

    def __init__(self, transport, name, db):
        super().__init__()
        self.daemon = True
        self.transport = transport
        self.name = name
        self.db = db

    def run(self):
        print('Здравствуйте, ' + self.name)
        self.print_help()
        while True:
            option = input('Введите команду: ')
            if option == 'message':
                self.create_message()
            elif option == 'help':
                self.print_help()
            elif option == 'users':
                with db_lock:
                    users = self.db.get_users()
                pprint(users)
            elif option == 'contacts':
                with db_lock:
                    contacts = self.db.get_contacts()
                pprint(contacts)
            elif option.startswith('add '):
                contact = ' '.join(option.split()[1:])
                with db_lock:
                    contact_exist = contact in self.db.get_contacts()
                    user_exist = contact in self.db.get_users()
                if not user_exist:
                    print('Пользователь не найден. Чтобы обновить и просмотреть список доступных пользователей, введите команду "users"')
                elif contact_exist:
                    print('Этот пользователь уже находится в вашем списке контактов')
                else:
                    with transport_lock:
                        try:
                            send_message(self.transport, {ACTION: ADD_CONTACT,
                                          ACCOUNT_NAME: self.name,
                                          TIME: time.time(),
                                          CONTACT: contact
                                          })
                            response = get_message(self.transport)
                            if RESPONSE not in response or response[RESPONSE] != 200:
                                raise ServerError('Упс. Что-то пошло не так')
                        except ServerError as e:
                            logger.error(e)
                    with db_lock:
                        self.db.add_contact(contact)
                    print('Контакт успешно создан')
            elif option.startswith('delete '):
                contact = ' '.join(option.split()[1:])
                with transport_lock:
                    send_message(self.transport, {ACTION: DEL_CONTACT,
                                  ACCOUNT_NAME: self.name,
                                  TIME: time.time(),
                                  CONTACT: contact
                                  })
                    response = get_message(self.transport)
                    if RESPONSE not in response or response[RESPONSE] != 200:
                        raise ServerError('Упс. Что-то пошло не так')
                with db_lock:
                    self.db.delete_contact(contact)
                print('Контакт успешно удалён')
            elif option == 'history':
                with db_lock:
                    history = self.db.get_message_history()
                pprint(history)
            elif option == 'exit':
                with transport_lock:
                    try:
                        send_message(self.transport, self.create_exit_message())
                    except:
                        pass
                    print('Завершение соединения.')
                    logger.info('Завершение работы по команде пользователя.')
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    def create_exit_message(self):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.name
        }

    def create_message(self):
        receiver = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.name,
            RECEIVER: receiver,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')
        with db_lock:
            self.db.save_message(self.name, receiver, message)
        with transport_lock:
            try:
                send_message(self.transport, message_dict)
                logger.info(f'Отправлено сообщение для пользователя {receiver}')
            except:
                logger.critical('Потеряно соединение с сервером.')
                exit(1)

    @staticmethod
    def print_help():
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('contacts - вывести список контактов')
        print('users - обновить и вывести список доступных пользователей')
        print('add [username] - добавить [username] в контакты')
        print('delete [username] - удалить [username] из контактов')
        print('history - вывести историю сообщений')
        print('exit - выход из программы')


@log
def message_from_server(sock, my_username):
    while True:
        try:
            message = get_message(sock)
            if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and RECEIVER in message \
                    and MESSAGE_TEXT in message and message[RECEIVER] == my_username:
                print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
            else:
                logger.error(f'Получено некорректное сообщение с сервера: {message}')
        except IncorrectDataRecivedError:
            logger.error(f'Не удалось декодировать полученное сообщение.')
        except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
            logger.critical(f'Потеряно соединение с сервером.')
            break


@log
def renew_users(name, transport, db):
    try:
        send_message(transport, {
            ACTION: GET_USERS,
            TIME: time.time(),
            ACCOUNT_NAME: name
        })
        response = get_message(transport)
        logger.info(f'Получено сообщение от сервера {response}')
        if RESPONSE in response and response[RESPONSE] == 202 and DATA in response and isinstance(response[DATA],
                                                                                                  list):
            with db_lock:
                db.renew_users(response[DATA])
        else:
            raise ServerError('Не удалось обновить список доступных пользователей')
    except ServerError as e:
        logger.error(e)
    try:
        send_message(transport, {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            ACCOUNT_NAME: name
        })
        response = get_message(transport)
        if RESPONSE in response and response[RESPONSE] == 202 and DATA in response and isinstance(response[DATA], list):
            contacts = response[DATA]
            with db_lock:
                for contact in contacts:
                    db.add_contact(contact)
        else:
            raise ServerError('Упс. Что-то пошло не так')
    except ServerError as e:
        logger.error(e)


@log
def create_presence(account_name):
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    logger.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
    return out


@log
def process_response_ans(message):
    logger.debug(f'Разбор приветственного сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        elif message[RESPONSE] == 400:
            raise ServerError(f'400 : {message[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if not 1023 < server_port < 65536:
        logger.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}. Допустимы адреса с 1024 до 65535. Клиент завершается.')
        exit(1)

    return server_address, server_port, client_name


def main():
    print('Консольный месседжер. Клиентский модуль.')

    server_address, server_port, client_name = arg_parser()

    if not client_name:
        client_name = input('Введите имя пользователя: ')

    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , порт: {server_port}, '
        f'имя пользователя: {client_name}')

    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        transport.settimeout(1)
        send_message(transport, create_presence(client_name))
        answer = process_response_ans(get_message(transport))
        logger.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        print(f'Установлено соединение с сервером для пользователя: {client_name}')
    except json.JSONDecodeError:
        logger.error('Не удалось декодировать полученную Json строку.')
        exit(1)
    except ServerError as error:
        logger.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        exit(1)
    except ReqFieldMissingError as missing_error:
        logger.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        exit(1)
    except (ConnectionRefusedError, ConnectionError):
        logger.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        exit(1)
    else:
        db = ClientDB(client_name)
        renew_users(client_name, transport, db)
        receiver = Receiver(transport, client_name, db)
        receiver.start()
        sender = Sender(transport, client_name, db)
        sender.start()
        logger.debug('Запущены процессы')

        while True:
            time.sleep(1)
            if receiver.is_alive() and sender.is_alive():
                continue
            break

        input()


if __name__ == '__main__':
    main()
