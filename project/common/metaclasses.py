import dis
from pprint import pprint


class ServerVerifier(type):

    def __init__(cls, clsname, bases, clsdict):

        attrs = set()
        methods = set()

        for f in clsdict:
            try:
                inst = dis.get_instructions(clsdict[f])
            except TypeError:
                pass
            else:
                for i in inst:

                    if i.opname == 'LOAD_GLOBAL' or i.opname == 'LOAD_METHOD':
                        methods.add(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        attrs.add(i.argval)

        if 'connect' in methods:
            raise TypeError
        if not ('AF_INET' in attrs and 'SOCK_STREAM' in attrs):
            raise TypeError

        super().__init__(clsname, bases, clsdict)


class ClientVerifier(type):

    def __init__(cls, clsname, bases, clsdict):
        methods = set()

        for f in clsdict:
            try:
                inst = dis.get_instructions(clsdict[f])
            except TypeError:
                pass
            else:
                for i in inst:

                    if i.opname == 'LOAD_GLOBAL' or i.opname == 'LOAD_METHOD':
                        methods.add(i.argval)

        if 'listen' in methods or 'accept' in methods:
            raise TypeError
        if not ('send_message' in methods or 'get_message' in methods):
            raise TypeError

        super().__init__(clsname, bases, clsdict)
