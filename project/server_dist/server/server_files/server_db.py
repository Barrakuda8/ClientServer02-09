from sqlalchemy import *
from sqlalchemy.orm import mapper, sessionmaker
import datetime


class ServerDB:
    """
    Класс, определяющий, создающий и изменяющий серверную базу данных
    """

    class User:
        def __init__(self, name, hash):
            self.id = None
            self.name = name
            self.last_login = datetime.datetime.now()
            self.hash = hash
            self.public_key = None

        def __repr__(self):
            return f'<User: {self.id}-{self.name}>'

    class ActiveUser:
        def __init__(self, user, login_time, login_ip, login_port):
            self.id = None
            self.user = user
            self.login_time = login_time
            self.login_ip = login_ip
            self.login_port = login_port

        def __repr__(self):
            return f'<Active User: {self.id}-{self.user}>'

    class LoginHistory:
        def __init__(self, user, login_time, login_ip, login_port):
            self.id = None
            self.user = user
            self.login_time = login_time
            self.login_ip = login_ip
            self.login_port = login_port

        def __repr__(self):
            return f'<Login: {self.id}-{self.user}-{self.login_time}>'

    class Contact:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

        def __repr__(self):
            return f'<Contact: {self.id}-{self.user}-{self.contact}>'

    class MessageHistory:
        def __init__(self, user):
            self.user = user
            self.sent = 0
            self.received = 0

        def __repr__(self):
            return f'<MessageHistory: {self.user}-{self.sent}-{self.received}>'

    def __init__(self, path):
        self.engine = create_engine(f'sqlite:///{path}.db3', echo=False, pool_recycle=7200,
                                    connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        users_table = Table('users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime),
                            Column('hash', String),
                            Column('public_key', Text)
                            )

        active_users_table = Table('active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('users.id'), unique=True),
                                   Column('login_time', DateTime),
                                   Column('login_ip', String),
                                   Column('login_port', String)
                                   )

        login_history_table = Table('login_history', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('users.id')),
                                    Column('login_time', DateTime),
                                    Column('login_ip', String),
                                    Column('login_port', String)
                                    )

        contacts_table = Table('contacts', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('user', ForeignKey('users.id')),
                               Column('contact', ForeignKey('users.id'))
                               )

        message_history_table = Table('message_history', self.metadata,
                                      Column('user', ForeignKey('users.id'), primary_key=True),
                                      Column('sent', Integer),
                                      Column('received', Integer)
                                      )

        self.metadata.create_all(self.engine)

        mapper(self.User, users_table)
        mapper(self.ActiveUser, active_users_table)
        mapper(self.LoginHistory, login_history_table)
        mapper(self.Contact, contacts_table)
        mapper(self.MessageHistory, message_history_table)

        self.session = sessionmaker(bind=self.engine)()
        self.session.query(self.ActiveUser).delete()
        self.session.commit()

    def add_user(self, name, hash):
        """
        :param name: имя нового пользователя
        :param hash: хэш пароля нового пользователя

        Метод, добавляющий в таблицу пользователей нового пользователя
        """

        user = self.User(name, hash)
        self.session.add(user)
        self.session.commit()
        self.session.add(self.MessageHistory(user.id))
        self.session.commit()

    def delete_user(self, name):
        """
        :param name: имя пользователя, которого нужно удалить

        Метод, удаляющий пользователя из базы данных
        """

        user = self.session.query(self.User).filter_by(name=name).first()
        self.session.query(self.ActiveUser).filter_by(user=user.id).delete()
        self.session.query(self.LoginHistory).filter_by(user=user.id).delete()
        self.session.query(self.Contact).filter_by(user=user.id).delete()
        self.session.query(self.Contact).filter_by(contact=user.id).delete()
        self.session.query(self.MessageHistory).filter_by(user=user.id).delete()
        self.session.query(self.User).filter_by(id=user.id).delete()
        self.session.commit()

    def user_login(self, name, ip, port, key):
        """
        :param name: имя пользователя
        :param ip: адрес подключения
        :param port: порт подключения
        :param key:  публичный ключ пользователя

        Метод, сохраняющий данные о входе пользователя на сервер в базе данных сервера
        """

        query = self.session.query(self.User).filter_by(name=name)

        if query.count():
            user = query.first()
            user.last_login = datetime.datetime.now()
            if user.public_key != key:
                user.public_key = key
        else:
            raise ValueError('Пользователь не зарегистрирован')

        self.session.add(self.ActiveUser(user.id, datetime.datetime.now(), ip, port))
        self.session.add(self.LoginHistory(user.id, datetime.datetime.now(), ip, port))

        self.session.commit()

    def user_logout(self, name):
        """
        :param name: имя пользователя

        Метод, удаляющий пользователя из таблицы активных пользователей
        """

        self.session.query(self.ActiveUser).filter_by(user=self.session.query(self.User)
                                                      .filter_by(name=name).first().id).delete()
        self.session.commit()

    def get_hash(self, name):
        """
        :param name: имя пользователя

        Метод, возвращающий хэш пароля пользователя из базы данных
        """

        return self.session.query(self.User).filter_by(name=name).first().hash

    def get_public_key(self, name):
        """
        :param name: имя пользователя

        Метод, возвращающий публичный ключ пользователя из базы данных
        """

        return self.session.query(self.User).filter_by(name=name).first().public_key

    def get_users(self):
        """
        Метод, возвращающий список доступных пользователей из базы данных сервера
        """

        return self.session.query(self.User.name, self.User.last_login).all()

    def check_user(self, name):
        """
        :param name: имя пользователя

        Метод, проверяющий зарегистрирован ли пользователь на сервере
        """

        if self.session.query(self.User).filter_by(name=name).count():
            return True
        else:
            return False

    def get_active_users(self):
        """
        Метод, возвращающий список активных пользователей из базы данных
        """

        return self.session.query(self.User.name, self.ActiveUser.login_ip, self.ActiveUser.login_port, self.ActiveUser.login_time).join(self.User).all()

    def get_login_history(self, name):
        """
        :param name: имя пользователя

        Метод, возвращающий истроию входа пользователя на сервер из базы данных
        """

        return self.session.query(self.LoginHistory).filter_by(user=self.session.query(self.User)
                                                               .filter_by(name=name).first().id).all()

    def get_contacts(self, name):
        """
        :param name: имя пользователя

        Метод, возвращающий список контактов пользователя из базы данных
        """

        return [contact[1] for contact in self.session.query(self.Contact, self.User.name).filter_by(user=self.session.query(self.User)
                                                          .filter_by(name=name).first().id).join(self.User, self.Contact.contact == self.User.id).all()]

    def get_message_history(self, name=None):
        """
        :param name: имя пользователя

        Метод возвращающий историю сообщений конкретного пользователя или всех пользователей
        """

        if not name:
            return self.session.query(self.User.name, self.User.last_login, self.MessageHistory.sent, self.MessageHistory.received).join(self.User).all()
        return self.session.query(self.User.name, self.User.last_login, self.MessageHistory.sent, self.MessageHistory.received)\
            .filter_by(user=self.session.query(self.User).filter_by(name=name).first().id).join(self.User).all()

    def add_contact(self, user_name, contact_name):
        """
        :param user_name: имя пользователя
        :param contact_name: имя пользователя, которого нужно добавить в контакты

        Метод, добавляющий одного пользователя в список контактов другого пользователя
        """

        user = self.session.query(self.User).filter_by(name=user_name).first().id
        contact = self.session.query(self.User).filter_by(name=contact_name).first().id
        self.session.add(self.Contact(user, contact))
        self.session.commit()

    def delete_contact(self, user_name, contact_name):
        """
        :param user_name: имя пользователя
        :param contact_name: имя пользователя, которого нужно удалить из контактов

        Метод, удаляющий одного пользователя из списка контактов другого пользователя
        """

        user = self.session.query(self.User).filter_by(name=user_name).first().id
        contact = self.session.query(self.User).filter_by(name=contact_name).first().id
        self.session.query(self.Contact).filter_by(user=user, contact=contact).delete()
        self.session.commit()

    def process_message(self, sender_name, receiver_name):
        """
        :param sender_name: имя отправителя
        :param receiver_name: имя получателя

        Метод, сохраняющий сообщение в таблице истории сообщений
        """

        sender = self.session.query(self.User).filter_by(name=sender_name).first().id
        receiver = self.session.query(self.User).filter_by(name=receiver_name).first().id

        self.session.query(self.MessageHistory).filter_by(user=sender).first().sent += 1
        self.session.query(self.MessageHistory).filter_by(user=receiver).first().received += 1

        self.session.commit()


if __name__ == '__main__':
    test_db = ServerDB()
    test_db.user_login('client_1', '192.168.1.4', 8080)
    test_db.user_login('client_2', '192.168.1.5', 7777)

    print(' ---- test_db.get_active_users() ----')
    print(test_db.get_active_users())

    test_db.user_logout('client_1')
    print(' ---- test_db.get_active_users() after logout client_1 ----')
    print(test_db.get_active_users())

    print(' ---- test_db.login_history(client_1) ----')
    print(test_db.get_login_history('client_1'))

    print(' ---- test_db.get_users() ----')
    print(test_db.get_users())

    print(' ---- test_db.get_contacts() of client_1----')
    print(test_db.get_contacts('client_1'))

    print(' ---- test_db.add_contact() client_2 to client_1----')
    test_db.add_contact('client_1', 'client_2')
    print(test_db.get_contacts('client_1'))

    print(' ---- test_db.delete_contact() client_2 of client_1----')
    test_db.delete_contact('client_1', 'client_2')
    print(test_db.get_contacts('client_1'))

    print(' ---- test_db.get_message_history() of client_1 and client_2----')
    print(test_db.get_message_history('client_1'))
    print(test_db.get_message_history('client_2'))

    print(' ---- test_db.count_message() client_1 to client_2----')
    test_db.process_message('client_1', 'client_2')
    print(test_db.get_message_history('client_1'))
    print(test_db.get_message_history('client_2'))

    test_db.user_logout('client_2')
    test_db.session.query(test_db.User).filter(test_db.User.name.in_(['client_1', 'client_2'])).delete()

    print(' ---- test_db.users_list() ----')
    print(test_db.get_users())
