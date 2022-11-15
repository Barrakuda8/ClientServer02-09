
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QLabel, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QTimer
from server_dist.server.server_files.stats_window import StatsWindow
from server_dist.server.server_files.config_window import ConfigWindow
from server_dist.server.server_files.add_user import AddUserDialog
from server_dist.server.server_files.delete_user import DeleteUserDialog


class MainWindow(QMainWindow):
    """
    Класс, определяющий и создающий основное окно графического интерфейса сервера
    """

    def __init__(self, db, server, config):
        super().__init__()

        self.db = db
        self.server = server
        self.config = config

        self.exitAction = QAction('Выход', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(qApp.quit)

        self.refresh_button = QAction('Обновить список', self)
        self.config_button = QAction('Настройки сервера', self)
        self.add_user_button = QAction('Регистрация пользователя', self)
        self.delete_user_button = QAction('Удаление пользователя', self)
        self.show_stats_button = QAction('История клиентов', self)

        self.statusBar()
        self.statusBar().showMessage('Server Working')
        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(self.exitAction)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_stats_button)
        self.toolbar.addAction(self.config_button)
        self.toolbar.addAction(self.add_user_button)
        self.toolbar.addAction(self.delete_user_button)

        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging Server alpha release')

        self.label = QLabel('Список подключённых клиентов:', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 25)

        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 45)
        self.active_clients_table.setFixedSize(780, 400)

        self.timer = QTimer()
        self.timer.timeout.connect(self.create_active_users_model)
        self.timer.start(1000)

        self.refresh_button.triggered.connect(self.create_active_users_model)
        self.show_stats_button.triggered.connect(self.show_stats)
        self.config_button.triggered.connect(self.server_config)
        self.add_user_button.triggered.connect(self.add_user)
        self.delete_user_button.triggered.connect(self.delete_user)

        self.show()

    def create_active_users_model(self):
        """
        Метод, заполняющий таблицу активных пользователей свежими данными из базы данных сервера
        """

        list_users = self.db.get_active_users()
        list = QStandardItemModel()
        list.setHorizontalHeaderLabels(
            ['Имя Клиента', 'IP Адрес', 'Порт', 'Время подключения'])
        for row in list_users:
            user, ip, port, time = row
            user = QStandardItem(user)
            user.setEditable(False)
            ip = QStandardItem(ip)
            ip.setEditable(False)
            port = QStandardItem(str(port))
            port.setEditable(False)
            time = QStandardItem(str(time.replace(microsecond=0)))
            time.setEditable(False)
            list.appendRow([user, ip, port, time])
        self.active_clients_table.setModel(list)
        self.active_clients_table.resizeColumnsToContents()
        self.active_clients_table.resizeRowsToContents()

    def show_stats(self):
        """
        Метод, вызывающий окно со статистикой пользователей
        """

        global stats_window
        stats_window = StatsWindow(self.db)
        stats_window.show()

    def server_config(self):
        """
        Метод, вызывающий окно изменения настроек сервера
        """

        global config_window
        config_window = ConfigWindow(self.config)

    def add_user(self):
        """
        Метод, вызывающий окно создания нового пользователя
        """

        global add_user_window
        add_user_window = AddUserDialog(self.db, self.server)
        add_user_window.show()

    def delete_user(self):
        """
        Метод, вызывающий окно удаления пользователя
        """

        global delete_user_window
        delete_user_window = DeleteUserDialog(self.db, self.server)
        delete_user_window.show()
