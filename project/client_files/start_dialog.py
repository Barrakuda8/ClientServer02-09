from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, QLabel, qApp


class UserNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ok_pressed = False

        self.setWindowTitle('Привет!')
        self.setFixedSize(175, 93)

        self.label = QLabel('Введите имя пользователя', self)
        self.label.setFixedSize(150, 10)
        self.label.move(10, 10)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(154, 20)
        self.client_name.move(10, 30)

        self.ok_button = QPushButton('Начать', self)
        self.ok_button.move(10, 60)
        self.ok_button.clicked.connect(self.click)

        self.cancel_button = QPushButton('Выход', self)
        self.cancel_button.move(90, 60)
        self.cancel_button.clicked.connect(qApp.exit)

        self.show()

    def click(self):
        if self.client_name.text():
            self.ok_pressed = True
            qApp.exit()


if __name__ == '__main__':
    app = QApplication([])
    dial = UserNameDialog()
    app.exec_()
