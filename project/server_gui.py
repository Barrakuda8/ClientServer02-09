import sys
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, QTableView, QDialog, QPushButton, \
    QLineEdit, QFileDialog
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()

        self.exit_button = QAction('Выход', self)
        self.exit_button.setShortcut('Ctrl+Q')
        self.exit_button.triggered.connect(qApp.quit)

        self.refresh_button = QAction('Обновить', self)
        self.show_message_history_button = QAction('История сообщений', self)
        self.config_button = QAction('Настройки сервера', self)

        self.statusBar()

        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(self.exit_button)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_message_history_button)
        self.toolbar.addAction(self.config_button)

        self.setWindowTitle('Super duper ultra next level messaging server!')
        self.setFixedSize(800, 600)

        self.label = QLabel('Список подключенных клиентов:', self)
        self.label.setFixedSize(400, 15)
        self.label.move(10, 35)

        self.active_clients_table = QTableView(self)
        self.active_clients_table.setFixedSize(780, 400)
        self.active_clients_table.move(10, 55)

        self.show()


class MessageHistoryWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('История сообщений клиентов')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(250, 650)
        self.close_button.clicked.connect(self.close)

        self.message_history_table = QTableView(self)
        self.message_history_table.setFixedSize(580, 620)
        self.message_history_table.move(10, 10)

        self.show()


class ConfigWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Настройки сервера')
        self.setFixedSize(365, 260)

        self.db_path_label = QLabel('Путь до файла базы данных: ', self)
        self.db_path_label.setFixedSize(250, 15)
        self.db_path_label.move(10, 10)

        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 20)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        self.db_path_select = QPushButton('Обзор', self)
        self.db_path_select.move(275, 28)
        self.db_path_select.clicked.connect(self.open_file_dialog)

        self.db_file_label = QLabel('Имя файла базы данных: ', self)
        self.db_file_label.setFixedSize(180, 15)
        self.db_file_label.move(10, 68)

        self.db_file = QLineEdit(self)
        self.db_file.setFixedSize(150, 20)
        self.db_file.move(200, 66)

        self.port_label = QLabel('Номер порта для соединений: ', self)
        self.port_label.setFixedSize(180, 15)
        self.port_label.move(10, 108)

        self.port = QLineEdit(self)
        self.port.setFixedSize(150, 20)
        self.port.move(200, 108)

        self.ip_label = QLabel('С какого IP принимать соединения: ', self)
        self.ip_label.setFixedSize(180, 15)
        self.ip_label.move(10, 148)

        self.ip_label_note = QLabel('Оставьте это поле пустым, чтобы\n принимать соединения с любых адресов', self)
        self.ip_label_note.setFixedSize(500, 30)
        self.ip_label_note.move(10, 168)

        self.ip = QLineEdit(self)
        self.ip.setFixedSize(150, 20)
        self.ip.move(200, 148)

        self.save_button = QPushButton('Сохранить', self)
        self.save_button.move(190, 200)
        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(275, 220)
        self.close_button.clicked.connect(self.close)

        self.show()

    def open_file_dialog(self):
        global dialog
        dialog = QFileDialog(self)
        self.db_path.insert(dialog.getExistingDirectory().replace('/', '\\'))


def func(obj):
    a = QStandardItem(obj)
    a.setEditable(False)
    return a


def create_active_users_model(db):
    active_users = db.get_active_users()
    table_model = QStandardItemModel()
    table_model.setHorizontalHeaderLabels(['Имя клиента', 'IP адрес', 'Порт', 'Время подключения'])

    for row in active_users:
        user, ip, port, time = row
        table_model.appendRow([func(user), func(ip), func(str(port)), func(str(time.replace(microsecond=0)))])

    return table_model


def create_message_history_model(db):
    message_history = db.get_message_history()
    table_model = QStandardItemModel()
    table_model.setHorizontalHeaderLabels(['Имя клиента', 'Сообщений отправлено', 'Сообщений получено'])

    for row in message_history:
        user, sent, received = row
        table_model.appendRow([func(user), func(str(sent)), func(str(received))])

    return table_model


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.statusBar().showMessage('Test Statusbar Message')
    test_list = QStandardItemModel(main_window)
    test_list.setHorizontalHeaderLabels(['Имя Клиента', 'IP Адрес', 'Порт', 'Время подключения'])
    test_list.appendRow(
        [QStandardItem('test1'), QStandardItem('192.198.0.5'), QStandardItem('23544'), QStandardItem('16:20:34')])
    test_list.appendRow(
        [QStandardItem('test2'), QStandardItem('192.198.0.8'), QStandardItem('33245'), QStandardItem('16:22:11')])
    main_window.active_clients_table.setModel(test_list)
    main_window.active_clients_table.resizeColumnsToContents()
    app.exec_()



