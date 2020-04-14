"""Module containing the client code.

The clients and servers communicate with each other using the JSON-RPC protocol.
See the 'protocol' module for what methods the servers support.
"""

import json
import socket
import threading 

import protocol
import socket_lib


class Client:
    """A client which eposes methods for easy communication with the servers."""

    def __init__(self, user_id, data_address, broadcast_address, 
                 on_new_message=None):
        """Initializes a new Client instance.

        On initialization, the Client initiates a message stream connection with
        the BroadcastServer in a separate thread. The thread listens for new
        messages from the BroadcastServer and calls on_new_message(message)
        for each new message. The call to on_new_message is locked to 
        synchronize it with the main thread.
        
        Args:
            user_id: The id of the user the client is handling.
            data_address: The (host, port) address of the DataServer.
            broadcast_address: The (host, port) address of the BroadcastServer.
            on_new_message: A function(message) callback which will be called
                each time a new message is received from the BroadcastServer.
        """
        self._user_id = user_id
        self._data_address = data_address
        self._broadcast_address = broadcast_address
        self._on_new_message = on_new_message 
        self._lock = threading.RLock()

        threading.Thread(target=self._stream_messages, daemon=True).start()

    # TODO(eugenhotaj): Find a better way to handle streaming messages.
    def _stream_messages(self):
        stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stream_socket.connect(self._broadcast_address)
        request = protocol.OpenStreamRequest(self._user_id)
        socket_lib.send_request('OpenStreamRequest', request.to_json(),
                                sock=stream_socket, keep_alive=True)
        while True:
            message = socket_lib.recv_message(stream_socket)
            message = json.loads(message)['result']['message']
            # TODO(eugenhotaj): Should we even lock here? Or leave it to the 
            # user to not trample on their data?
            with self._lock:
                self._on_new_message(message)

    def get_users(self, user_ids):
        request = protocol.GetUsersRequest(user_ids)
        response = socket_lib.send_request(
                'GetUsers', request.to_json(), address=self._data_address)
        return response['users']

    def get_chats(self, user_id):
        request = protocol.GetChatsRequest(user_id)
        response = socket_lib.send_request(
                'GetChats', request.to_json(), address=self._data_address)
        return response['chats']

    def get_messages(self, chat_id):
        request = protocol.GetMessagesRequest(chat_id)
        response = socket_lib.send_request(
                'GetMessages', request.to_json(), address=self._data_address)
        return response['messages'] 

    def insert_message(self, chat_id, user_id, message_text):
        request = protocol.InsertMessageRequest(chat_id, user_id, message_text)
        response = socket_lib.send_request(
                'InsertMessage', request.to_json(), address=self._data_address)
        return response['message']
