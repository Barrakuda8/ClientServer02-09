from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox, QApplication, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSlot, QEvent, Qt
import logging
import sys
sys.path.append('../')
from client_files.main_window_ui import MainClientWindowUI
from client_files.add_contact_dialog import AddContactDialog
from client_files.delete_contact_dialog import DeleteContactDialog
from common.errors import ServerError

logger = logging.getLogger('client_dist')


class ClientMainWindow(QMainWindow):
    def __init__(self, transport, db):
        super().__init__()
        self.transport = transport
        self.db = db

        self.ui = MainClientWindowUI(self)

        self.ui.menu_exit.triggered.connect(qApp.exit)
        self.ui.send_button.clicked.connect(self.send_message)

        self.ui.add_contact_button.clicked.connect(self.add_contact_dialog)
        self.ui.menu_add_contact.triggered.connect(self.add_contact_dialog)

        self.ui.remove_contact_button.clicked.connect(self.delete_contact_dialog)
        self.ui.menu_del_contact.triggered.connect(self.delete_contact_dialog)

        self.contacts_model = None
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.ui.messages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.messages.setWordWrap(True)

        self.ui.contacts.doubleClicked.connect(self.select_active_user)

        self.renew_clients()
        self.set_disabled_input()
        self.show()

    def set_disabled_input(self):
        self.ui.label_new_message.setText('Для выбора получателя '
                                          'дважды кликните на нем в окне контактов.')
        self.ui.text_message.clear()
        if self.history_model:
            self.history_model.clear()

        self.ui.clear_button.setDisabled(True)
        self.ui.send_button.setDisabled(True)
        self.ui.text_message.setDisabled(True)

    def renew_message_history(self):
        list_messages = sorted(self.db.get_message_history(self.current_chat),
                               key=lambda m: m[3])
        if not self.history_model:
            self.history_model = QStandardItemModel()
            self.ui.messages.setModel(self.history_model)
        self.history_model.clear()
        length = len(list_messages)
        start_index = 0
        if length > 20:
            start_index = length - 20
        for i in range(start_index, length):
            item = list_messages[i]
            if item[1] == self.transport.name:
                mess = QStandardItem(f'Входящее от {item[3].replace(microsecond=0)}:\n {item[2]}')
                mess.setEditable(False)
                mess.setBackground(QBrush(QColor(255, 213, 213)))
                mess.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(mess)
            else:
                mess = QStandardItem(f'Исходящее от {item[3].replace(microsecond=0)}:\n {item[2]}')
                mess.setEditable(False)
                mess.setTextAlignment(Qt.AlignRight)
                mess.setBackground(QBrush(QColor(204, 255, 204)))
                self.history_model.appendRow(mess)
        self.ui.messages.scrollToBottom()

    def select_active_user(self):
        self.current_chat = self.ui.contacts.currentIndex().data()
        self.set_active_user()

    def set_active_user(self):
        self.ui.label_new_message.setText(f'Введите сообщение для {self.current_chat}:')
        self.ui.clear_button.setDisabled(False)
        self.ui.send_button.setDisabled(False)
        self.ui.text_message.setDisabled(False)
        self.renew_message_history()

    def renew_clients(self):
        contacts_list = self.db.get_contacts()
        self.contacts_model = QStandardItemModel()
        for i in sorted(contacts_list):
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.contacts.setModel(self.contacts_model)

    def add_contact_dialog(self):
        global select_dialog
        select_dialog = AddContactDialog(self.transport, self.db)
        select_dialog.ok_button.clicked.connect(lambda: self.add_contact_action(select_dialog))
        select_dialog.show()

    def add_contact_action(self, item):
        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    def add_contact(self, new_contact):
        try:
            self.transport.add_contact(new_contact)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.db.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            logger.info(f'Успешно добавлен контакт {new_contact}')
            self.messages.information(self, 'Успех', 'Контакт успешно добавлен.')

    def delete_contact_dialog(self):
        global remove_dialog
        remove_dialog = DeleteContactDialog(self.db)
        remove_dialog.ok_button.clicked.connect(lambda: self.delete_contact(remove_dialog))
        remove_dialog.show()

    def delete_contact(self, item):
        selected = item.selector.currentText()
        try:
            self.transport.delete_contact(selected)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.db.delete_contact(selected)
            self.renew_clients()
            logger.info(f'Успешно удалён контакт {selected}')
            self.messages.information(self, 'Успех', 'Контакт успешно удалён.')
            item.close()
            if selected == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    def send_message(self):
        message_text = self.ui.text_message.toPlainText()
        self.ui.text_message.clear()
        if not message_text:
            return
        try:
            self.transport.send_message(self.current_chat, message_text)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        except (ConnectionResetError, ConnectionAbortedError):
            self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
            self.close()
        else:
            self.db.save_message(self.current_chat, 'out', message_text)
            logger.debug(f'Отправлено сообщение для {self.current_chat}: {message_text}')
            self.renew_message_history()

    @pyqtSlot(str)
    def new_message_slot(self, sender):
        if sender == self.current_chat:
            self.renew_message_history()
        else:
            if sender in self.db.get_contacts():
                if self.messages.question(self, 'Новое сообщение',
                                          f'Получено новое сообщение от {sender}, '
                                          f'открыть чат с ним?', QMessageBox.Yes,
                                          QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    self.set_active_user()
            else:
                print('NO')
                if self.messages.question(self, 'Новое сообщение',
                                          f'Получено новое сообщение от {sender}.\n '
                                          f'Данного пользователя нет в вашем контакт-листе.\n'
                                          f' Добавить в контакты и открыть чат с ним?',
                                          QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(sender)
                    self.current_chat = sender
                    self.set_active_user()

    @pyqtSlot()
    def connection_lost_slot(self):
        self.messages.warning(self, 'Сбой соединения', 'Потеряно соединение с сервером. ')
        self.close()

    def make_connection(self, trans_obj):
        trans_obj.new_message.connect(self.new_message_slot)
        trans_obj.connection_lost.connect(self.connection_lost_slot)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    from client_db import ClientDB
    db = ClientDB('test1')
    from transport import ClientTransport
    transport = ClientTransport(7777, '127.0.0.1', 'test1', db)
    window = ClientMainWindow(transport, db)
    sys.exit(app.exec_())

