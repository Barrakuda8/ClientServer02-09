import sys
import logging
from PyQt5.QtWidgets import QDialog, QLabel, QComboBox, QPushButton, QApplication
from PyQt5.QtCore import Qt


logger = logging.getLogger('client_dist')


class DeleteContactDialog(QDialog):
    """
    Класс графического интерфейса окна удаления одного пользователя из списка контактов другого пользователя
    """
    def __init__(self, db):
        super().__init__()
        self.db = db

        self.setWindowTitle('Выберите контакт для удаления')
        self.setFixedSize(350, 120)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        self.selector_label = QLabel('Выберите контакт для удаления: ', self)
        self.selector_label.setFixedSize(200, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 20)
        self.selector.move(10, 30)
        self.selector.addItems(sorted(self.db.get_contacts()))

        self.ok_button = QPushButton('Удалить', self)
        self.ok_button.setFixedSize(100, 30)
        self.ok_button.move(230, 20)

        self.cancel_button = QPushButton('Отмена', self)
        self.cancel_button.setFixedSize(100, 30)
        self.cancel_button.move(230, 60)
        self.cancel_button.clicked.connect(self.close)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    from client_db import ClientDB
    db = ClientDB('test1')
    window = DeleteContactDialog(db)
    db.add_contact('test1')
    db.add_contact('test2')
    print(db.get_contacts())
    window.selector.addItems(sorted(db.get_contacts()))
    window.show()
    app.exec_()
