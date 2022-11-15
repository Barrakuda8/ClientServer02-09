from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, QLabel, qApp


class UserNameDialog(QDialog):
    """
    Класс, определяющий и создающий окно аутентификции для текущего пользователя
    """

    def __init__(self):
        super().__init__()

        self.ok_pressed = False

        self.setWindowTitle('Привет!')
        self.setFixedSize(175, 135)

        self.label_name = QLabel('Введите имя пользователя', self)
        self.label_name.setFixedSize(150, 10)
        self.label_name.move(10, 10)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(154, 20)
        self.client_name.move(10, 30)

        self.ok_button = QPushButton('Начать', self)
        self.ok_button.move(10, 105)
        self.ok_button.clicked.connect(self.click)

        self.cancel_button = QPushButton('Выход', self)
        self.cancel_button.move(90, 105)
        self.cancel_button.clicked.connect(qApp.exit)

        self.label_password = QLabel('Введите пароль:', self)
        self.label_password.move(10, 55)
        self.label_password.setFixedSize(150, 15)

        self.client_password = QLineEdit(self)
        self.client_password.setFixedSize(154, 20)
        self.client_password.move(10, 75)
        self.client_password.setEchoMode(QLineEdit.Password)

        self.show()

    def click(self):
        """
        Метод, проверяющий наличие введённых данных и закрывающий окно аутентификации
        """
        if self.client_name.text() and self.client_password.text():
            self.ok_pressed = True
            qApp.exit()


if __name__ == '__main__':
    app = QApplication([])
    dial = UserNameDialog()
    app.exec_()
