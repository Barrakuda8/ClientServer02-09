from sqlalchemy import *
from sqlalchemy.orm import mapper, sessionmaker
import datetime


class ServerDB:

    class User:
        def __init__(self, name):
            self.id = None
            self.name = name
            self.last_login = datetime.datetime.now()

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
                            Column('last_login', DateTime)
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

    def user_login(self, name, ip, port):

        query = self.session.query(self.User).filter_by(name=name)

        if query.count():
            user = query.first()
            user.last_login = datetime.datetime.now()
        else:
            user = self.User(name)
            self.session.add(user)
            self.session.commit()
            self.session.add(self.MessageHistory(user.id))
            self.session.commit()

        self.session.add(self.ActiveUser(user.id, datetime.datetime.now(), ip, port))
        self.session.add(self.LoginHistory(user.id, datetime.datetime.now(), ip, port))

        self.session.commit()

    def user_logout(self, name):

        self.session.query(self.ActiveUser).filter_by(user=self.session.query(self.User)
                                                      .filter_by(name=name).first().id).delete()
        self.session.commit()

    def get_users(self):
        return self.session.query(self.User.name, self.User.last_login).all()

    def get_active_users(self):
        return self.session.query(self.User.name, self.ActiveUser.login_ip, self.ActiveUser.login_port, self.ActiveUser.login_time).join(self.User).all()

    def get_login_history(self, name):
        return self.session.query(self.LoginHistory).filter_by(user=self.session.query(self.User)
                                                               .filter_by(name=name).first().id).all()

    def get_contacts(self, name):
        return [contact[1] for contact in self.session.query(self.Contact, self.User.name).filter_by(user=self.session.query(self.User)
                                                          .filter_by(name=name).first().id).join(self.User, self.Contact.contact == self.User.id).all()]

    def get_message_history(self, name=None):
        if not name:
            return self.session.query(self.User.name, self.MessageHistory.sent, self.MessageHistory.received).join(self.User).all()
        return self.session.query(self.User.name, self.MessageHistory.sent, self.MessageHistory.received).filter_by(user=self.session.query(self.User)
                                                                 .filter_by(name=name).first().id).join(self.User).all()

    def add_contact(self, user_name, contact_name):
        user = self.session.query(self.User).filter_by(name=user_name).first().id
        contact = self.session.query(self.User).filter_by(name=contact_name).first().id
        self.session.add(self.Contact(user, contact))
        self.session.commit()

    def delete_contact(self, user_name, contact_name):
        user = self.session.query(self.User).filter_by(name=user_name).first().id
        contact = self.session.query(self.User).filter_by(name=contact_name).first().id
        self.session.query(self.Contact).filter_by(user=user, contact=contact).delete()
        self.session.commit()

    def process_message(self, sender_name, receiver_name):
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
