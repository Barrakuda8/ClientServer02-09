from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, QLabel, QMessageBox
from PyQt5.QtCore import Qt
import hashlib
import binascii


class AddUserDialog(QDialog):
    """
    Класс, определяющий и создающий окно создания нового пользователя
    """

    def __init__(self, db, server):
        super().__init__()

        self.db = db
        self.server = server

        self.setWindowTitle('Регистрация')
        self.setFixedSize(175, 183)
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.label_username = QLabel('Введите имя пользователя:', self)
        self.label_username.move(10, 10)
        self.label_username.setFixedSize(150, 15)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(154, 20)
        self.client_name.move(10, 30)

        self.label_passwd = QLabel('Введите пароль:', self)
        self.label_passwd.move(10, 55)
        self.label_passwd.setFixedSize(150, 15)

        self.client_passwd = QLineEdit(self)
        self.client_passwd.setFixedSize(154, 20)
        self.client_passwd.move(10, 75)
        self.client_passwd.setEchoMode(QLineEdit.Password)
        self.label_conf = QLabel('Введите подтверждение:', self)
        self.label_conf.move(10, 100)
        self.label_conf.setFixedSize(150, 15)

        self.client_conf = QLineEdit(self)
        self.client_conf.setFixedSize(154, 20)
        self.client_conf.move(10, 120)
        self.client_conf.setEchoMode(QLineEdit.Password)

        self.ok_button = QPushButton('Сохранить', self)
        self.ok_button.move(10, 150)
        self.ok_button.clicked.connect(self.save_data)

        self.cancel_button = QPushButton('Выход', self)
        self.cancel_button.move(90, 150)
        self.cancel_button.clicked.connect(self.close)

        self.messages = QMessageBox()

        self.show()

    def save_data(self):
        """
        Метод, проверяющий введённые данные, хэширующий введённый пароль и записывающий нового пользователя в базу
        данных сервера
        """

        if not self.client_name.text():
            self.messages.critical(
                self, 'Ошибка', 'Не указано имя пользователя')
            return
        elif self.client_passwd.text() != self.client_conf.text():
            self.messages.critical(
                self, 'Ошибка', 'Введённые пароли не совпадают')
            return
        elif self.db.check_user(self.client_name.text()):
            self.messages.critical(
                self, 'Ошибка', 'Пользователь уже существует')
            return
        else:
            password_bytes = self.client_passwd.text().encode('utf-8')
            salt = self.client_name.text().lower().encode('utf-8')
            hash = hashlib.pbkdf2_hmac('sha512', password_bytes, salt, 10000)
            self.db.add_user(
                self.client_name.text(),
                binascii.hexlify(hash))
            self.messages.information(
                self, 'Успех', 'Пользователь успешно зарегистрирован.')
            self.server.service_update_lists()
            self.close()


if __name__ == '__main__':
    app = QApplication([])
    from server_db import ServerDB
    db = ServerDB('../../../server_db.db3')
    import os
    import sys
    path1 = os.path.join(os.getcwd(), '../../..')
    sys.path.insert(0, path1)
    from core import MessageProcessor
    server = MessageProcessor('127.0.0.1', 7777, db)
    dial = AddUserDialog(db, server)
    app.exec_()
