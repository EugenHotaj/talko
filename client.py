"""Module containing the client code.

See the 'socket_lib' module for the client-server communication protocol.
"""

import argparse
from datetime import datetime
import socket

import constants
import database_lib
import socket_lib


def main(user_id, path):
    database = database_lib.Database(path)

    user_name = f'user_{user_id}'
    try:
        database.insert_user(user_id, user_name)
    except:
        # The user already exists.
        pass

    # "User interface" for the terminal version of the chat. The terminal
    # blocks on input so we won't actually see any messages until we receive
    # some input. We could fix this, but it's not worth it.
    print(f'Welcome {user_name}!')
    while True:
        print('Select an option:\n  1: View chats\n  2: New chat')
        option = int(input('> '))
        if option == 1:
            chats = database.list_chats(user_id)
            if chats:
                print('Select an open chat to continue messaging:')
                for i, chat in enumerate(chats):
                    print(f'{i+1}: {chat}')
                chat_id = int(input('> '))
                break
            else:
                print('No chats found, going back to main menu.')
                continue
        elif option == 2:
            print('Insert the user_id you want to chat with.')
            receiver_id = int(input('> '))
            if not database.get_user(receiver_id):
                raise Exception(f'No user found with user_id "{receiver_id}"')
            # If a chat already exists with the user, resue the chat.
            chat_id = database.get_chat_id_for_user_ids(user_id, receiver_id)
            if chat_id is None:
                chat_id = database.insert_chat(user_id, receiver_id)
            break
        else:
            raise Exception(f'Unrecognized option "{option}"')

    messages = database.list_messages(chat_id)
    for message in messages:
        # TODO(eugenhotaj): Use the user_name instead of user_id when displaying
        # messages. We could update Database.list_messages() to join on the 
        # Users table and return messages with user_names. Another option is to
        # create a Database.get_users(user_ids) method and join the user_names
        # to the user_ids in code, which might be faster than the join, 
        # especially if we don't index on user_names.
        date_and_time = datetime.fromtimestamp(
                int(message.message_ts / constants.MILLIS_PER_SEC))
        print(f'{message.user_id} @ {date_and_time}: {message.message_text}')

    # Connect the client socket to the server.
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((constants.LOCALHOST, constants.LOCALHOST_PORT))
    client_socket.setblocking(False)

    while True:
        # First, receive and display all messages from the server.
        messages = socket_lib.recv_all_messages(client_socket)
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
        socket_lib.send_message(client_socket, message)


if __name__ == '__main__':
    # Parse flags.
    parser = argparse.ArgumentParser()
    parser.add_argument('--user_id', type=int, required=True, 
                        help='Id for the connected user')
    # TODO(eugenhotaj): I'm yakking from how terrible this is. All db 
    # communication should be pushed to the server and the client should simply
    # request the data it wants from the server (maybe via a REST API).
    parser.add_argument('--db_path', type=str, required=True, 
                        help='Path to the SQLite chat database')
    FLAGS = parser.parse_args()
    main(FLAGS.user_id, FLAGS.db_path)
