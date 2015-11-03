from socket import *
import json
import game_builder

def wait_to_recieve():
    server_port = 12000
    server_socket = socket(AF_INET, SOCK_DGRAM)
    server_socket.bind(('', server_port))
    while True:
        json_data, client_address = server_socket.recvfrom(2048)
        data_list = json.loads(json_data)
        game_builder.build_game(data_list)
        print "recieved"
        return json_data
wait_to_recieve()
