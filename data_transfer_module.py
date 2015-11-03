from socket import *
import json

def transfer(json_data):
    server_port = 12000
    server_name = 'localhost'
    client_socket = socket(AF_INET, SOCK_DGRAM)
    
    client_socket.sendto(json_data,(server_name, server_port))
    client_socket.close()
