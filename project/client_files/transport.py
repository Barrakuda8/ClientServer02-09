import socket
import sys
import time
import logging
import threading
from PyQt5.QtCore import pyqtSignal, QObject

sys.path.append('../')
from common.utils import *
from common.variables import *
from common.errors import ServerError


logger = logging.getLogger('client_dist')

transport_lock = threading.Lock()


class ClientTransport(threading.Thread, QObject):

    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, port, ip, name, db):
        threading.Thread.__init__(self)
        QObject.__init__(self)
        self.daemon = True
        self.transport = None
        self.name = name
        self.db = db

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

        try:
            with transport_lock:
                send_message(self.transport, self.create_presence())
                self.process_response_ans(get_message(self.transport))
        except (OSError, json.JSONDecodeError):
            logger.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')

        logger.info('Соединение с сервером успешно установлено.')

        try:
            self.renew_users()
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

    def create_presence(self):
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.name
            }
        }
        logger.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.name}')
        return out

    def process_response_ans(self, message):
        logger.debug(f'Разбор сообщения: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
            else:
                logger.debug(f'Принят неизвестный код подтверждения {message[RESPONSE]}')
        elif ACTION in message and message[ACTION] == MESSAGE and \
                SENDER in message and MESSAGE_TEXT in message and RECEIVER in message \
                and message[RECEIVER] == self.name:
            self.db.save_message(message[SENDER], self.name, message[MESSAGE_TEXT])
            logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
            self.new_message.emit(message[SENDER])

    def add_contact(self, contact):
        with transport_lock:
            send_message(self.transport, {ACTION: ADD_CONTACT,
                                          ACCOUNT_NAME: self.name,
                                          TIME: time.time(),
                                          CONTACT: contact
                                          })
            self.process_response_ans(get_message(self.transport))

    def delete_contact(self, contact):
        with transport_lock:
            send_message(self.transport, {ACTION: DEL_CONTACT,
                                          ACCOUNT_NAME: self.name,
                                          TIME: time.time(),
                                          CONTACT: contact
                                          })
            self.process_response_ans(get_message(self.transport))

    def transport_shutdown(self):
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
            ans = get_message(self.transport)
            self.process_response_ans(ans)
            logger.info(f'Отправлено сообщение для пользователя {receiver}')

    def run(self):
        logger.debug('Запущен процесс - приёмник сообщений с сервера.')
        while self.running:
            time.sleep(1)
            with transport_lock:
                self.transport.settimeout(0.5)
                try:
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
                else:
                    logger.debug(f'Принято сообщение с сервера: {message}')
                    self.process_response_ans(message)
                finally:
                    self.transport.settimeout(5)
