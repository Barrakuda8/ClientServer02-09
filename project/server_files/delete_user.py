from PyQt5.QtWidgets import QDialog, QLabel, QComboBox, QPushButton, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem


class DeleteUserDialog(QDialog):
    """
    Класс, определяющий и создающий окно удаления пользователя
    """

    def __init__(self, db, server):
        super().__init__()
        self.db = db
        self.server = server

        self.setFixedSize(350, 120)
        self.setWindowTitle('Удаление пользователя')
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        self.selector_label = QLabel(
            'Выберите пользователя для удаления:', self)
        self.selector_label.setFixedSize(200, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 20)
        self.selector.move(10, 30)

        self.ok_button = QPushButton('Удалить', self)
        self.ok_button.setFixedSize(100, 30)
        self.ok_button.move(230, 20)
        self.ok_button.clicked.connect(self.remove_user)

        self.cancel_button = QPushButton('Отмена', self)
        self.cancel_button.setFixedSize(100, 30)
        self.cancel_button.move(230, 60)
        self.cancel_button.clicked.connect(self.close)

        self.all_users_fill()

    def all_users_fill(self):
        """
        Метод, заполняющий меню выбора пользователя пользователями из базы данных
        """

        self.selector.addItems([item[0] for item in self.db.get_users()])

    def remove_user(self):
        """
        Метод, провоцирующий удаление пользователя из базы данных сервера и отключающий его от сервера
        """

        self.db.delete_user(self.selector.currentText())
        if self.selector.currentText() in self.server.names:
            sock = self.server.names[self.selector.currentText()]
            del self.server.names[self.selector.currentText()]
            self.server.remove_client(sock)
        self.server.service_update_lists()
        self.close()


if __name__ == '__main__':
    app = QApplication([])
    from server_db import ServerDB
    db = ServerDB('../server_db.db3')
    import os
    import sys
    path1 = os.path.join(os.getcwd(), '..')
    sys.path.insert(0, path1)
    from core import MessageProcessor
    server = MessageProcessor('127.0.0.1', 7777, db)
    dial = DeleteUserDialog(db, server)
    dial.show()
    app.exec_()
