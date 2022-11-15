import socket
import sys
import time
import logging
import threading
from PyQt5.QtCore import pyqtSignal, QObject
import hashlib
import binascii
import hmac
sys.path.append('../')
from common.utils import *
from common.variables import *
from common.errors import ServerError


logger = logging.getLogger('client_dist')

transport_lock = threading.Lock()


class ClientTransport(threading.Thread, QObject):
    """
    Класс, осуществляющий функционал клиента
    """

    new_message = pyqtSignal(dict)
    connection_lost = pyqtSignal()
    message_205 = pyqtSignal()

    def __init__(self, port, ip, name, db, password, keys):
        """
        Метод __init__, который помимо стандартных своих функций проверяет пароль пользователя и устанавливает
        соединение с сервером
        """
        threading.Thread.__init__(self)
        QObject.__init__(self)
        self.daemon = True
        self.name = name
        self.db = db
        self.password = password
        self.keys = keys

        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.settimeout(5)

        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                logger.debug('Установлено соединение с сервером')
                break
            time.sleep(1)

        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        password_bytes = self.password.encode('utf-8')
        salt = self.name.lower().encode('utf-8')
        password_hash = binascii.hexlify(hashlib.pbkdf2_hmac('sha512', password_bytes, salt, 10000))
        logger.debug(f'Password hash ready: {password_hash}')

        pubkey = self.keys.publickey().export_key().decode('ascii')

        with transport_lock:
            presence = {
                ACTION: PRESENCE,
                TIME: time.time(),
                USER: {
                    ACCOUNT_NAME: self.name,
                    PUBLIC_KEY: pubkey
                }
            }
            logger.debug(f"Presense message = {presence}")
            try:
                send_message(self.transport, presence)
                ans = get_message(self.transport)
                logger.debug(f'Server response = {ans}.')
                if RESPONSE in ans:
                    if ans[RESPONSE] == 400:
                        raise ServerError(ans[ERROR])
                    elif ans[RESPONSE] == 511:
                        ans_data = ans[BIN]
                        hash = hmac.new(password_hash, ans_data.encode('utf-8'), 'MD5').digest()
                        my_ans = RESPONSE_511
                        my_ans[BIN] = binascii.b2a_base64(hash).decode('ascii')
                        send_message(self.transport, my_ans)
                        self.process_response_ans(get_message(self.transport))
            except (OSError, json.JSONDecodeError) as err:
                logger.debug(f'Connection error.', exc_info=err)
                raise ServerError('Сбой соединения в процессе авторизации.')

        try:
            self.renew_users()
            self.renew_contacts()
        except OSError as err:
            if err.errno:
                logger.critical(f'Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            logger.error('Timeout соединения при обновлении списков пользователей.')
        except json.JSONDecodeError:
            logger.critical(f'Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')

        self.running = True

    def renew_users(self):
        """
        Метод, обновляющий таблицу доступных пользователей в базе данных текущего пользователя
        """

        with transport_lock:
            send_message(self.transport, {
                ACTION: GET_USERS,
                TIME: time.time(),
                ACCOUNT_NAME: self.name
            })
            response = get_message(self.transport)
        logger.info(f'Получено сообщение от сервера {response}')
        if RESPONSE in response and response[RESPONSE] == 202 and DATA in response and isinstance(response[DATA],
                                                                                                  list):
            self.db.renew_users(response[DATA])
        else:
            logger.error('Не удалось обновить список доступных пользователей')

    def renew_contacts(self):
        """
        Метод, обновляющий таблицу контактов в базе данных текущего пользователя
        """

        with transport_lock:
            send_message(self.transport, {
                ACTION: GET_CONTACTS,
                TIME: time.time(),
                ACCOUNT_NAME: self.name
            })
            response = get_message(self.transport)
        logger.info(f'Получено сообщение от сервера {response}')
        if RESPONSE in response and response[RESPONSE] == 202 and DATA in response and isinstance(response[DATA],
                                                                                                  list):
            for contact in response[DATA]:
                self.db.add_contact(contact)
        else:
            logger.error('Упс. Что-то пошло не так')

    def get_key(self, user):
        """
        :param user: имя пользователя, чей ключ нужно получить
        Метод, запрашивающий публичный ключ данного пользователя
        """

        logger.debug(f'Запрос публичного ключа для {user}')
        req = {
            ACTION: GET_PUBLIC_KEY,
            TIME: time.time(),
            ACCOUNT_NAME: user
        }
        with transport_lock:
            send_message(self.transport, req)
            response = get_message(self.transport)
        if RESPONSE in response and response[RESPONSE] == 511:
            return response[BIN]
        else:
            logger.error(f'Не удалось получить ключ собеседника{user}.')

    def process_response_ans(self, message):
        """
        :param message: словарь, содержащий данный о полученном сообщении
        Метод, обрабатывающий полученное сообщение
        """

        logger.debug(f'Разбор сообщения: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
            elif message[RESPONSE] == 205:
                self.renew_users()
                self.renew_contacts()
                self.message_205.emit()
            else:
                logger.debug(f'Принят неизвестный код подтверждения {message[RESPONSE]}')
        elif ACTION in message and message[ACTION] == MESSAGE and \
                SENDER in message and MESSAGE_TEXT in message and RECEIVER in message \
                and message[RECEIVER] == self.name:
            logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
            self.new_message.emit(message)

    def add_contact(self, contact):
        """
        :param contact: имя пользователя, которого нужно добавил в контакты
        Метод, запрашивающий добавление другого пользователя в контакты текущего пользователя
        """

        with transport_lock:
            send_message(self.transport, {ACTION: ADD_CONTACT,
                                          ACCOUNT_NAME: self.name,
                                          TIME: time.time(),
                                          CONTACT: contact
                                          })
            self.process_response_ans(get_message(self.transport))

    def delete_contact(self, contact):
        """
        :param contact: имя пользователя, которого нужно удалить из контактов текущего пользователя
        Метод, запрашивающий удаление другого пользователя из списка текущего пользователя
        """

        with transport_lock:
            send_message(self.transport, {ACTION: DEL_CONTACT,
                                          ACCOUNT_NAME: self.name,
                                          TIME: time.time(),
                                          CONTACT: contact
                                          })
            self.process_response_ans(get_message(self.transport))

    def transport_shutdown(self):
        """
        Метод, осуществляющий завершение работы клиента
        """

        self.running = False
        with transport_lock:
            try:
                send_message(self.transport, {
                        ACTION: EXIT,
                        TIME: time.time(),
                        ACCOUNT_NAME: self.name
                    })
            except OSError:
                pass
        logger.info('Завершение работы')
        time.sleep(0.5)

    def send_message(self, receiver, message):
        """
        :param receiver: имя получателя сообщения
        :param message: текст сообщения
        Метод, запрашивающий отправление сообщения от текущего пользователя другому пользователю
        """

        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.name,
            RECEIVER: receiver,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')

        with transport_lock:
            send_message(self.transport, message_dict)
            self.process_response_ans(get_message(self.transport))
            logger.info(f'Отправлено сообщение для пользователя {receiver}')

    def run(self):
        """
        Метод, отслеживающий входящие сообщения и осуществляющий их приём
        """

        logger.debug('Запущен процесс - приёмник сообщений с сервера.')
        while self.running:
            time.sleep(1)
            message = None
            with transport_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        logger.critical(f'Потеряно соединение с сервером.')
                        self.running = False
                        self.connection_lost.emit()
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError, TypeError):
                    logger.debug(f'Потеряно соединение с сервером.')
                    self.running = False
                    self.connection_lost.emit()
                finally:
                    self.transport.settimeout(5)

            if message:
                logger.debug(f'Принято сообщение с сервера: {message}')
                self.process_response_ans(message)