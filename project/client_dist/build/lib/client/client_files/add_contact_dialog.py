import logging
from PyQt5.QtWidgets import QDialog, QLabel, QComboBox, QPushButton, QApplication
from PyQt5.QtCore import Qt
import sys

logger = logging.getLogger('client_dist')


class AddContactDialog(QDialog):
    """
    Класс графического интерфейса окна добавления одного пользователя в список контактов текущего пользователя
    """

    def __init__(self, transport, db):
        super().__init__()
        self.transport = transport
        self.db = db

        self.setWindowTitle('Выберите контакт для добавления')
        self.setFixedSize(350, 120)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        self.selector_label = QLabel('Выберите контакт для добавления: ', self)
        self.selector_label.setFixedSize(200, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 20)
        self.selector.move(10, 30)

        self.refresh_button = QPushButton('Обновить список', self)
        self.refresh_button.setFixedSize(100, 30)
        self.refresh_button.move(60, 60)

        self.ok_button = QPushButton('Добавить', self)
        self.ok_button.setFixedSize(100, 30)
        self.ok_button.move(230, 20)

        self.cancel_button = QPushButton('Отмена', self)
        self.cancel_button.setFixedSize(100, 30)
        self.cancel_button.move(230, 60)
        self.cancel_button.clicked.connect(self.close)

        self.get_possible_contacts()
        self.refresh_button.clicked.connect(self.renew_possible_contacts)

    def get_possible_contacts(self):
        """
        Метод, создающий список пользователей, доступных для добавления в список контактов текущего пользователя
        """
        self.selector.clear()
        contacts = set(self.db.get_contacts())
        users = set(self.db.get_users())
        users.remove(self.transport.name)
        self.selector.addItems(users - contacts)

    def renew_possible_contacts(self):
        """
        Метод, обеспечивающий обновление информации в списке пользователей, доступных для добавления в список
        контактов текущего пользователя
        """

        try:
            self.transport.renew_users()
        except OSError:
            pass
        else:
            logger.debug('Обновление списка пользователей с сервера выполнено')
            self.get_possible_contacts()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    from client_db import ClientDB
    db = ClientDB('test1')
    from transport import ClientTransport
    transport = ClientTransport(7777, '127.0.0.1', db, 'test1')
    window = AddContactDialog(transport, db)
    window.show()
    app.exec_()
