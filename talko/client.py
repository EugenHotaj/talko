"""Module containing the client code.

The clients and servers communicate with each other using the JSON-RPC protocol.
See the 'protocol' module for what methods the servers support.
"""

import json
import socket

from talko import protocol
from talko import socket_lib


class Client:
    """A client which exposes methods for communication with the servers."""

    def __init__(self, data_address, broadcast_address):
        """Initializes a new Client instance.
        
        Args:
            data_address: The (host, port) address of the DataServer.
            broadcast_address: The (host, port) address of the BroadcastServer.
        """
        self._data_address = data_address
        self._broadcast_address = broadcast_address

    def open_stream(self, user_id):
        """Opens a new message stream for the given user_id.

        WARNING: This function returns a *blocking* generator which yields new
        messages as they are received from the server.
        """

        stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stream_socket.connect(self._broadcast_address)
        request = protocol.OpenStreamRequest(user_id)
        socket_lib.send_request('OpenStreamRequest', request.to_json(),
                                sock=stream_socket, keep_alive=True)
        while True:
            message = socket_lib.recv_message(stream_socket)
            message = json.loads(message)['result']['message']
            yield message 

    def get_user(self, user_id):
        request = protocol.GetUserRequest(user_id)
        response = socket_lib.send_request(
                'GetUser', request.to_json(), address=self._data_address)
        return response

    def get_chats(self, user_id):
        request = protocol.GetChatsRequest(user_id)
        response = socket_lib.send_request(
                'GetChats', request.to_json(), address=self._data_address)
        return response

    def get_messages(self, chat_id):
        request = protocol.GetMessagesRequest(chat_id)
        response = socket_lib.send_request(
                'GetMessages', request.to_json(), address=self._data_address)
        return response

    def insert_message(self, chat_id, user_id, message_text):
        request = protocol.InsertMessageRequest(chat_id, user_id, message_text)
        response = socket_lib.send_request(
                'InsertMessage', request.to_json(), address=self._data_address)
        return response
