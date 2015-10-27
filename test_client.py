import cPickle as pickle
from socket import *

server_port = 12000
server_name = 'localhost'
client_socket = socket(AF_INET, SOCK_DGRAM)

class Test(object):
    def __init__(self, name):
        self.name = name

t = Test("test")
message = pickle.dumps(t)

client_socket.sendto(message,(server_name, server_port))
client_socket.close()
