"""Module containing the client code.

The clients and servers communicate with each other using the JSON-RPC protocol.
See the 'protocol' module for what methods the servers support.
"""

import argparse
from datetime import datetime
import json
import socket

import constants
import socket_lib


def _send_request(method, params):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((constants.LOCALHOST, constants.DATA_PORT))
    request = {'method': method, 'params': params, 'id': 0}
    socket_lib.send_message(sock, json.dumps(request))
    response = socket_lib.recv_message(sock)
    sock.close()
    return json.loads(response)['result']


def main(user_id):
    # "User interface" for the terminal version of the chat. The terminal
    # blocks on input so we won't actually see any messages until we receive
    # some input. We could fix this, but it's not worth it.
    user_name = 'Fake User'
    print(f'Welcome {user_name}!')
    while True:
        print('Select an option:\n  0: View chats\n  1: New chat')
        option = int(input('> '))
        if option == 0:
            response = _send_request('GetChats', {'user_id': user_id})
            chats = response['chats']
            if chats:
                print('Select an open chat to continue messaging:')
                for i, chat in enumerate(chats):
                    print(f'{i}: {chat["chat_name"]}')
                chat_id = chats[int(input('> '))]['chat_id']
                break
            else:
                print('No chats found, going back to main menu.')
                continue
        elif option == 1:
            print('Type the csv of users you want to chat with:')
            user_ids = [int(user_id) for user_id in input('> ').split(',')]
            user_ids.append(user_id)
            params = {'chat_name': 'Some random name', 'user_ids': user_ids}
            chat_id = _send_request('InsertChat', params)
            break
        else:
            raise Exception(f'Unrecognized option "{option}"')

    response = _send_request('GetMessages', {'chat_id': chat_id})
    messages = response['messages']
    for message in messages:
        # TODO(eugenhotaj): Use the user_name instead of user_id when displaying
        # messages. We could update Database.list_messages() to join on the 
        # Users table and return messages with user_names. Another option is to
        # create a Database.get_users(user_ids) method and join the user_names
        # to the user_ids in code, which might be faster than the join, 
        # especially if we don't index on user_names.
        date_and_time = datetime.fromtimestamp(
                int(message['message_ts'] / constants.MILLIS_PER_SEC))
        user_id, message_text = message['user_id'], message['message_text' ]
        print(f'{user_id} @ {date_and_time}: {message_text}')

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((constants.LOCALHOST, constants.BROADCAST_PORT))
    sock.setblocking(False)
    while True:
        # First, receive and display all messages from the server.
        messages = socket_lib.recv_all_messages(sock)
        for message in messages:
            sender, message_text = message['user_id'], message['message_text']
            print(f'{sender:>3}: {message_text}')

        message_text = input(f'{user_name}> ')
            
        # Then send back a response.
        message = {
                'chat_id': chat_id,
                'user_id': user_id,
                'user_name': user_name,
                'message_text': message_text
        }
        request = {'method': 'BroadcastRequest', 'params': message, 'id': 0}
        socket_lib.send_message(sock, json.dumps(request))


if __name__ == '__main__':
    # Parse flags.
    parser = argparse.ArgumentParser()
    parser.add_argument('--user_id', type=int, required=True, 
                        help='Id for the connected user')
    FLAGS = parser.parse_args()
    main(FLAGS.user_id)
