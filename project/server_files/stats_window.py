from PyQt5.QtWidgets import QDialog, QPushButton, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


class StatsWindow(QDialog):
    """
    Класс, определяющий и создающий окно статистики пользователей
    """

    def __init__(self, db):
        super().__init__()

        self.db = db

        self.setWindowTitle('Статистика клиентов')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(250, 650)
        self.close_button.clicked.connect(self.close)

        self.stat_table = QTableView(self)
        self.stat_table.move(10, 10)
        self.stat_table.setFixedSize(580, 620)

        self.create_stats_model()

    def create_stats_model(self):
        """
        Метод, заполняющий таблицу статистики пользователей данными из базы данных
        """

        stat_list = self.db.get_message_history()

        list = QStandardItemModel()
        list.setHorizontalHeaderLabels(
            ['Имя Клиента', 'Последний раз входил', 'Сообщений отправлено', 'Сообщений получено'])
        for row in stat_list:
            user, last_seen, sent, received = row
            user = QStandardItem(user)
            user.setEditable(False)
            last_seen = QStandardItem(str(last_seen.replace(microsecond=0)))
            last_seen.setEditable(False)
            sent = QStandardItem(str(sent))
            sent.setEditable(False)
            received = QStandardItem(str(received))
            received.setEditable(False)
            list.appendRow([user, last_seen, sent, received])
        self.stat_table.setModel(list)
        self.stat_table.resizeColumnsToContents()
        self.stat_table.resizeRowsToContents()
