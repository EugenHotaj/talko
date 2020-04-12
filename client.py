"""Module containing the client code.

The clients and servers communicate with each other using the JSON-RPC protocol.
See the 'protocol' module for what methods the servers support.
"""

import argparse
from datetime import datetime
import json
import multiprocessing
import socket

import constants
import socket_lib


def get_input(expected_type=str):
    try:
        return expected_type(input('> '))
    except EOFError:
        pass


def chat_loop(chat_id, user_id, address):
    response = socket_lib.send_request(
            'GetMessages', {'chat_id': chat_id}, address=address)
    messages = response['messages']
    for message in messages:
        # TODO(eugenhotaj): Display the user_name instead of user_id.
        date_and_time = datetime.fromtimestamp(
               int(message['message_ts'] / constants.MILLIS_PER_SEC))
        sender_id, message_text = message['user_id'], message['message_text']
        print(f'{sender_id} @ {date_and_time}: {message_text}')

    while True:
        message_text = get_input(expected_type=str)
        if message_text is None:
            break
        message = {
                'chat_id': chat_id,
                'user_id': user_id,
                'message_text': message_text
        }
        socket_lib.send_request('InsertMessage', message, address=address)


def main(user_id):
    data_address = (constants.LOCALHOST, constants.DATA_PORT)
    broadcast_address = (constants.LOCALHOST, constants.BROADCAST_PORT)

    def stream_messages(user_id):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(broadcast_address)
        resp = socket_lib.send_request('OpenStreamRequest', {'user_id': user_id}, 
                                sock=sock, keep_alive=True)
        while True:
            message = socket_lib.recv_message(sock)
            message = json.loads(message)['result']
            user_id, message_text = message['sender_id'], message['message_text']
            print(f'STREAM: {user_id} @ TODO: {message_text}')

    multiprocessing.Process(target=stream_messages, args=(user_id,)).start()

    user_name = 'Fake User'
    print(f'Welcome {user_name}!')
    while True:
        print('Main menu:\n    0: View chats\n    1: New chat')
        option = get_input(expected_type=int)
        if option is None:
            break
        elif option == 0:
            chats = socket_lib.send_request(
                    'GetChats', {'user_id': user_id}, address=data_address)
            chats = chats['chats']
            if chats:
                print('Available chats:')
                for i, chat in enumerate(chats):
                    chat_name = chat['chat_name']
                    print(f'    {i}: {chat_name}')
                option = get_input(expected_type=int)
                if option is None:
                    continue
                chat_id = chats[option]['chat_id']
                chat_loop(chat_id, user_id, data_address)
            else:
                print('No chats found.')
                continue
        elif option == 1:
            print('Type the csv of users you want to chat with:')
            user_ids = [int(user_id) for user_id in input('> ').split(',')]
            user_ids.append(user_id)
            params = {'chat_name': 'Some random name', 'user_ids': user_ids}
            chat_id = socket_lib.send_request(
                    'InsertChat', params, address=data_address)['chat_id']
            chat_loop(chat_id, data_address)
        

if __name__ == '__main__':
    # Parse flags.
    parser = argparse.ArgumentParser()
    parser.add_argument('--user_id', type=int, required=True, 
                        help='Id for the connected user')
    FLAGS = parser.parse_args()
    main(FLAGS.user_id)
