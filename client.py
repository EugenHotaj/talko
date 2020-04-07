"""Module containing the client code.

See the 'socket_lib' module for the client-server communication protocol.
"""

import argparse
import socket
import time

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

    print(f'Welcome {user_name}!')
    while True:
        print('Select an option:\n  0: View chats\n  1: New chat')
        option = int(input('> '))
        if option == 0:
            chats = database.list_chats(user_id)
            if chats:
                print('Select an open chat to message:')
                for i, chat in enumerate(chats):
                    print(f'{i}: {chat}')
                raise NotImplementedError('Cannot continue chats just yet.')
            else:
                print('No chats found, going back to main menu.')
                continue
        elif option == 1:
            print('Insert the user_id you want to chat with.')
            receiver_id = int(input('> '))
            if not database.get_user(receiver_id):
                raise Exception(f'No user found with user_id "{receiver_id}"')
            # If a chat already exists with the user, resue the chat.
            chat_id = database.get_chat_id_for_user_ids(user_id, receiver_id)
            if not chat_id:
                chat_id = database.insert_chat(user_id, receiver_id)
            messages = database.list_messages(chat_id)
            raise NotImplementedError('Cannot send messages just yet.')
        else:
            raise Exception(f'Unrecognized option "{option}"')

    # # Connect the client socket to the server.
    # client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # client_socket.connect((constants.LOCALHOST, constants.LOCALHOST_PORT))
    # client_socket.setblocking(False)

    # while True:
    #     # First, receive and display all messages from the server.
    #     messages = socket_lib.recv_all_messages(client_socket)
    #     for message in messages:
    #         receiver = message['receiver']
    #         assert receiver == user_id 
    #         sender, text = message['sender'], message['text']
    #         print(f'{sender:>3} says: {text}')
    #         
    #     # Then send back a response.
    #     message = {
    #             'sender': user_id,
    #             'receiver': 0,
    #             'text': f"Hello {0}, I'm {user_name}."
    #     }
    #     socket_lib.send_message(client_socket, message)
    #     time.sleep(1.)


if __name__ == '__main__':
    # Parse flags.
    parser = argparse.ArgumentParser()
    parser.add_argument('--user_id', type=int, required=True, 
                        help='Id for the connected user')
    # TODO(eugenhotaj): I'm yakking from how terrible this is. All db 
    # communication should be pushed to the server and the client should simply
    # request the data it wants from the server (maybe via a REST API).
    parser.add_argument('--path', type=str, required=True, 
                        help='Path to the SQLite chat database')
    FLAGS = parser.parse_args()
    main(FLAGS.user_id, FLAGS.path)
