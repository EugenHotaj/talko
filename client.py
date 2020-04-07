"""Module containing the client code.

See the 'socket_lib' module for the client-server communication protocol.
"""

import socket
import time

import constants
import socket_lib

sender = 1
receiver = 0


if __name__ == '__main__':
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((constants.LOCALHOST, constants.LOCALHOST_PORT))
    client_socket.setblocking(False)

    client_id = sender
    i = 0
    while True:
        # First, receive and display all messages from the server.
        messages = socket_lib.recv_all_messages(client_socket)
        for message in messages:
            from_, to, text = message['from'], message['to'], message['text']
            assert to == client_id
            print(f'{client_id:>3} says: {text}')
            
        # Then send back a response.
        message = {
                'from': client_id,
                'to': receiver,
                'text': f"Hello there, I'm client {client_id}."
        }
        socket_lib.send_message(client_socket, message)
        print(f'sent message {i}')
        i += 1
        time.sleep(1.)
