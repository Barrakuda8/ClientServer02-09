from PyQt5 import QtCore, QtGui, QtWidgets


class MainClientWindowUI(object):
    def __init__(self, MainClientWindow):
        MainClientWindow.setObjectName("MainClientWindow")
        MainClientWindow.resize(756, 534)
        MainClientWindow.setMinimumSize(QtCore.QSize(756, 534))

        self.central_widget = QtWidgets.QWidget(MainClientWindow)
        self.central_widget.setObjectName("central_widget")

        self.label_contacts = QtWidgets.QLabel(self.central_widget)
        self.label_contacts.setGeometry(QtCore.QRect(10, 0, 101, 16))
        self.label_contacts.setObjectName("label_contacts")

        self.add_contact_button = QtWidgets.QPushButton(self.central_widget)
        self.add_contact_button.setGeometry(QtCore.QRect(10, 450, 121, 31))
        self.add_contact_button.setObjectName("add_contact_button")

        self.remove_contact_button = QtWidgets.QPushButton(self.central_widget)
        self.remove_contact_button.setGeometry(QtCore.QRect(140, 450, 121, 31))
        self.remove_contact_button.setObjectName("remove_contact_button")

        self.label_history = QtWidgets.QLabel(self.central_widget)
        self.label_history.setGeometry(QtCore.QRect(300, 0, 391, 21))
        self.label_history.setObjectName("label_history")

        self.text_message = QtWidgets.QTextEdit(self.central_widget)
        self.text_message.setGeometry(QtCore.QRect(300, 360, 441, 71))
        self.text_message.setObjectName("text_message")

        self.label_new_message = QtWidgets.QLabel(self.central_widget)
        self.label_new_message.setGeometry(QtCore.QRect(300, 330, 450, 16))
        self.label_new_message.setObjectName("label_new_message")

        self.contacts = QtWidgets.QListView(self.central_widget)
        self.contacts.setGeometry(QtCore.QRect(10, 20, 251, 411))
        self.contacts.setObjectName("contacts")

        self.messages = QtWidgets.QListView(self.central_widget)
        self.messages.setGeometry(QtCore.QRect(300, 20, 441, 301))
        self.messages.setObjectName("messages")

        self.send_button = QtWidgets.QPushButton(self.central_widget)
        self.send_button.setGeometry(QtCore.QRect(610, 450, 131, 31))
        self.send_button.setObjectName("send_button")

        self.clear_button = QtWidgets.QPushButton(self.central_widget)
        self.clear_button.setGeometry(QtCore.QRect(460, 450, 131, 31))
        self.clear_button.setObjectName("clear_button")

        MainClientWindow.setCentralWidget(self.central_widget)

        self.menubar = QtWidgets.QMenuBar(MainClientWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 756, 21))
        self.menubar.setObjectName("menubar")

        self.menu = QtWidgets.QMenu(self.menubar)
        self.menu.setObjectName("menu")

        self.menu_2 = QtWidgets.QMenu(self.menubar)
        self.menu_2.setObjectName("menu_2")

        MainClientWindow.setMenuBar(self.menubar)

        self.statusBar = QtWidgets.QStatusBar(MainClientWindow)
        self.statusBar.setObjectName("statusBar")

        MainClientWindow.setStatusBar(self.statusBar)

        self.menu_exit = QtWidgets.QAction(MainClientWindow)
        self.menu_exit.setObjectName("menu_exit")

        self.menu_add_contact = QtWidgets.QAction(MainClientWindow)
        self.menu_add_contact.setObjectName("menu_add_contact")

        self.menu_del_contact = QtWidgets.QAction(MainClientWindow)
        self.menu_del_contact.setObjectName("menu_del_contact")

        self.menu.addAction(self.menu_exit)
        self.menu_2.addAction(self.menu_add_contact)
        self.menu_2.addAction(self.menu_del_contact)
        self.menu_2.addSeparator()
        self.menubar.addAction(self.menu.menuAction())
        self.menubar.addAction(self.menu_2.menuAction())

        self.retranslateUi(MainClientWindow)
        self.clear_button.clicked.connect(self.text_message.clear)
        QtCore.QMetaObject.connectSlotsByName(MainClientWindow)

    def retranslateUi(self, MainClientWindow):
        _translate = QtCore.QCoreApplication.translate
        MainClientWindow.setWindowTitle(_translate("MainClientWindow", "Чат Программа alpha release"))
        self.label_contacts.setText(_translate("MainClientWindow", "Список контактов:"))
        self.add_contact_button.setText(_translate("MainClientWindow", "Добавить контакт"))
        self.remove_contact_button.setText(_translate("MainClientWindow", "Удалить контакт"))
        self.label_history.setText(_translate("MainClientWindow", "История сообщений:"))
        self.label_new_message.setText(_translate("MainClientWindow", "Введите новое сообщение:"))
        self.send_button.setText(_translate("MainClientWindow", "Отправить сообщение"))
        self.clear_button.setText(_translate("MainClientWindow", "Очистить поле"))
        self.menu.setTitle(_translate("MainClientWindow", "Файл"))
        self.menu_2.setTitle(_translate("MainClientWindow", "Контакты"))
        self.menu_exit.setText(_translate("MainClientWindow", "Выход"))
        self.menu_add_contact.setText(_translate("MainClientWindow", "Добавить контакт"))
        self.menu_del_contact.setText(_translate("MainClientWindow", "Удалить контакт"))

