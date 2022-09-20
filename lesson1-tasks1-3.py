import threading
from ipaddress import ip_address
import tabulate
import pprint
from subprocess import Popen, PIPE
from threading import Thread
import platform

result = {'Доступные узлы': [], 'Недоступные узлы': []}
result_lock = threading.Lock()


class Ping(Thread):

    def __init__(self, ip, i=0):
        super().__init__()
        self.daemon = True
        try:
            self.ip = ip_address(ip) + i
            self.bad_ip = None
        except ValueError:
            self.ip = None
            self.bad_ip = ip

    def run(self):
        if not self.bad_ip:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            process = Popen(['ping', param, '2', '-w', '1', str(self.ip)], stdout=PIPE)
            stdout = process.communicate()
            to_return = self.ip
        else:
            stdout = None
            to_return = self.bad_ip
        result_lock.acquire()
        if stdout and to_return not in result['Доступные узлы']:
            result['Доступные узлы'].append(to_return)
        elif not stdout and to_return not in result['Недоступные узлы']:
            result['Недоступные узлы'].append(to_return)
        result_lock.release()


def host_ping(ips):
    threads = []

    for ip in ips:
        thread = Ping(ip)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    print(result)


def host_range_ping_tab(func):
    def wrapper(*args):
        func(*args)
        if result['Доступные узлы'] or result['Недоступные узлы']:
            print(tabulate.tabulate(result, headers='keys', tablefmt='pipe', stralign='center'))
    return wrapper


# task 3 - @host_range_ping_tab
def host_range_ping(ip, ip_range):
    try:
        if str(ip_address(ip)).split('.')[-1] != '0':
            print('введено некорректное значение')
            return
    except ValueError:
        result['Недоступные узлы'].append(ip)
        return

    if ip_range > 256 or ip_range < 1:
        print('введено значение вне диапазона')
        return

    threads = []

    for i in range(ip_range):
        thread = Ping(ip, i)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    # task 2 - print(result)


# task 1 - host_ping(['8.8.8.0', '9.1.2.3', '2.3.45.12', 'a', 1])
# task 2 - host_range_ping('8.8.8.0', 1)

