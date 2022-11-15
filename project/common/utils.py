from common.variables import *
import json
import sys
sys.path.append('../')
from common.decos import log


@log
def get_message(client):
    """
    :param client: сокет с которого должно прийти сообщение
    Функция, осуществляющая приём сообщения с определенного сокета
    """

    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    json_response = encoded_response.decode(ENCODING)
    response = json.loads(json_response)
    if isinstance(response, dict):
        return response
    else:
        raise TypeError


@log
def send_message(sock, message):
    """
    :param sock: сокет, на который нужно отправить сообщение
    :param message: словарь сообщения для отправки
    Функция, осуществляющая отправку сообщений на определённый сокет
    """

    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)
