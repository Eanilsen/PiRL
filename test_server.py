import cPickle as pickle
from socket import *
server_port = 12000
server_socket = socket(AF_INET, SOCK_DGRAM)
server_socket.bind(('', server_port))

class Test(object):
    def __init__(self, name):
        self.name = name

while True:
    message, client_address = server_socket.recvfrom(2048)
    message = pickle.loads(message)
    print message.name
