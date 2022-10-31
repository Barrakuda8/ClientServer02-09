from sqlalchemy import *
from sqlalchemy.orm import mapper, sessionmaker
import datetime
import os


class ClientDB:

    class User:
        def __init__(self, name):
            self.id = None
            self.name = name

        def __repr__(self):
            return self.name

    class Contact:
        def __init__(self, name):
            self.id = None
            self.name = name

        def __repr__(self):
            return self.name

    class MessageHistory:
        def __init__(self, sender, receiver, message):
            self.id = None
            self.sender = sender
            self.receiver = receiver
            self.time = datetime.datetime.now()
            self.message = message

        def __repr__(self):
            return f'From {self.sender} to {self.receiver} at {self.time}: \n {self.message}'

    def __init__(self, client_name):
        self.client_name = client_name
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), f'client_base_{self.client_name}.db3')
        self.engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                    connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        users_table = Table('users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True)
                            )

        contacts_table = Table('contacts', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('name', String, unique=True)
                               )

        message_history_table = Table('message_history', self.metadata,
                                      Column('id', Integer, primary_key=True),
                                      Column('sender', String),
                                      Column('receiver', String),
                                      Column('time', DateTime),
                                      Column('message', Text)
                                      )

        self.metadata.create_all(self.engine)

        mapper(self.User, users_table)
        mapper(self.Contact, contacts_table)
        mapper(self.MessageHistory, message_history_table)

        self.session = sessionmaker(bind=self.engine)()
        self.session.query(self.Contact).delete()
        self.session.commit()

    def get_users(self):
        return [user[0] for user in self.session.query(self.User.name).all()]

    def get_contacts(self):
        return [contact[0] for contact in self.session.query(self.Contact.name).all()]

    def get_message_history(self, contact):
        history = self.session.query(self.MessageHistory).filter(or_(self.MessageHistory.sender == contact, self.MessageHistory.receiver == contact))
        return [(message.sender, message.receiver, message.message, message.time)
                for message in history]

    def add_contact(self, contact):
        if not self.session.query(self.Contact).filter_by(name=contact).count():
            self.session.add(self.Contact(contact))
            self.session.commit()

    def delete_contact(self, contact):
        self.session.query(self.Contact).filter_by(name=contact).delete()
        self.session.commit()

    def save_message(self, sender, receiver, message):
        self.session.add(self.MessageHistory(sender, receiver, message))
        self.session.commit()

    def renew_users(self, users):
        self.session.query(self.User).delete()
        for user in users:
            self.session.add(self.User(user))
        self.session.commit()


if __name__ == '__main__':
    test_db = ClientDB('client_1')

    print(' ---- test_db.get_users() ----')
    print(test_db.get_users())

    print(' ---- test_db.renew_users(["client_2", "client_3"]) ----')
    test_db.renew_users(["client_2", "client_3"])
    print(test_db.get_users())

    print(' ---- test_db.get_contacts() ----')
    print(test_db.get_contacts())

    print(' ---- test_db.add_contact("client_2") ----')
    test_db.add_contact("client_2")
    print(test_db.get_contacts())

    print(' ---- test_db.add_contact("client_2") ----')
    test_db.add_contact("client_2")

    print(' ---- test_db.add_contact("client_14") ----')
    test_db.add_contact("client_14")

    print(' ---- test_db.delete_contact("client_2") ----')
    test_db.delete_contact("client_2")
    print(test_db.get_contacts())

    print(' ---- test_db.save_message("client_1", "client_2", "hi") ---- \n'
          ' ---- test_db.get_message_history()                      ---- ')
    test_db.save_message("client_1", "client_2", "hi")
    print(test_db.get_message_history())
