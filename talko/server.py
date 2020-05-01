"""Definitions of the BroadcastServer and DataServer."""

import os
import argparse
import json
import logging
import multiprocessing 
import socket
import time

from talko import constants
from talko import database_client 
from talko import protocol
from talko import socket_lib


# NOTE(eugenhotaj): We use processes instead of threads to get around the GIL.
MAX_WORKERS = 10000

# # TODO(eugenhotaj): Add more robust logging capabilities.
# os.makedirs('/tmp/talko', exist_ok=True)
# logging.basicConfig(
#         filename='/tmp/talko/log.info',
#         filemode='w',
#         level=logging.INFO,
#         format='%(asctime)s %(levelname)s %(pathname)s:%(lineno)s %(message)s', 
#         datefmt='%m/%d/%Y %I:%M:%S %p')

class Server:
    """A Server which can handle concurrent requests via processes.

    Requests are processed via the handle_request() method which must be 
    overridden by the subclasses.
    """

    def __init__(self, address, max_workers=None):
        """Initializes a new Server instance.
        
        Args:
            address: The (host, port) tuple address to bind this server to.
            max_workers: The total number of workers to use for serving 
                requests. Requests which exceed the number of available workers
                are dropped.
        """
        self._address = address
        self._max_workers = max_workers or MAX_WORKERS

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

    def handle_request(self, client_socket):
        """Handles a request. 

        This method must be implemented by the subclasses.
        
        Args:
            client_socket: The socket of a newly connected client.
        Returns:
            Whether to keep the client_socket alive (True) or close it (False).
        """
        raise NotImplementedError()

    def _handle_request(self, client_socket, host, port):
        # logging.info(f'Connection from {host}:{port} established')
        try:
            keep_alive = self.handle_request(client_socket)
            if not keep_alive:
                client_socket.close()
                # logging.info(f'Connection from {host}:{port} closed')
        except Exception:
            client_socket.close()
            raise

    def _keep_if_alive(self, worker):
        try:
            is_alive = worker.is_alive()
            if not is_alive:
                worker.close()
        except ValueError:
            return False
        return is_alive

    def serve_forever(self):
        """Serves requests indefinitely using a separate process per request."""
        self._socket.bind(self._address)
        self._socket.listen()

        workers = []
        while True:
            result = self._socket.accept()
            workers = [w for w in workers if self._keep_if_alive(worker)]
            if result:
                client_socket, (host, port) = result
                if len(workers) < self._max_workers:
                    worker = multiprocessing.Process(
                            target=self._handle_request, 
                            args=(client_socket, host, port))
                    worker.start()
                    workers.append(worker)
                else:
                    # If the server is overloaded, shed any new connections.
                    client_socket.shutdown(socket.SHUT_RDWR)
                    client_socket.close()
                    # logging.warning(f'Connection from {host}:{port} shed')
 

class DataServer(Server):
    """A Server which handles reading and writing conversation data.

    Unlike the BroadcastServer, the DataServer operates via a request/response
    protocol. This means that it handles exactly one request per client 
    connection and responds back with exactly one response, after which the 
    connection to the client socket is terminated.

    If the client sends multiple requests on the same socket, only the first
    request is processed and subsequent requests are ignored.
    """

    def __init__(self, address, broadcast_address, db_path, max_workers=None):
        """Initializes a new DataServer instance.

        Args:
            address: See the base class.
            broadcast_address: The (host, port) address of the BroadcastServer
                which will handle broadcasting new messages to online users.
            db_path: The path to the SQLite chat database.
        """
        super().__init__(address, max_workers=max_workers)
        self._broadcast_address = broadcast_address
        self._db_path = db_path

    def handle_request(self, client_socket):
        """See the base class."""
        db_client = database_client.DatabaseClient(self._db_path)
        request = socket_lib.recv_message(client_socket)
        request = json.loads(request)
        method, params, id_ = request['method'], request['params'], request['id']

        if method == 'GetUser':
            request = protocol.GetUserRequest.from_json(params)
            user = db_client.get_user(request.user_id)
            response = protocol.GetUserResponse(user)
        elif method == 'InsertUser':
            request = protocol.InsertUserRequest.from_json(params)
            user = db_client.insert_user(request.user_name)
            response = protocol.InsertUserResponse(user)
        elif method == 'GetChats':
            # TODO(eugen): This is horrible!!! We need to be smarter about
            # how we fill out the chat objects. Either via joins, or by bulk
            # requesting users and messages.
            request = protocol.GetChatsRequest.from_json(params)
            chats = []
            for chat in db_client.get_chats(request.user_id):
                users = {}
                for p in db_client.get_participants(chat.chat_id):
                    users[p.user_id] = protocol.User(p.user_id, p.user_name)
                messages = []
                for m in db_client.get_messages(chat.chat_id):
                    message = protocol.Message(
                            m.message_id,
                            m.chat_id,
                            users[m.user_id],
                            m.message_text,
                            m.message_ts)
                    messages.append(message)
                # TODO(eugenhotaj): Move chat_name logic to a helper function.
                users = list(users.values())
                chat_name = chat.chat_name
                if len(users) == 2:
                    chat_name = [
                            user.user_name for user in users 
                            if user.user_id != request.user_id
                    ][0]
                chat = protocol.Chat(
                    chat.chat_id, chat_name, users, messages)
                chats.append(chat)
            chats = sorted(chats, key=lambda chat: chat.messages[-1].message_ts,
            response = protocol.GetChatsResponse(chats)
        elif method == 'InsertChat':
            request = protocol.InsertChatRequest.from_json(params)
            user_ids = request.user_ids
            chat_id = None
            if len(user_ids) == 2:
                chat = db_client.get_private_chat_id(*user_ids)
            if not chat_id:
                chat = db_client.insert_chat(request.chat_name, user_ids)
            response = protocol.InsertChatResponse(chat)
        elif method == 'GetMessages':
            # TODO(eugen): This is horrible!!! We need to be smarter about
            # how we fill out the chat objects. Either via joins, or by bulk
            # requesting users and messages.
            request = protocol.GetMessagesRequest.from_json(params)
            users = {}
            for p in db_client.get_participants(request.chat_id):
                users[p.user_id] = protocol.User(p.user_id, p.user_name)
            messages = []
            for m in db_client.get_messages(request.chat_id):
                message = protocol.Message(
                        m.message_id,
                        m.chat_id,
                        users[m.user_id],
                        m.message_text,
                        m.message_ts)
                messages.append(message)
            response = protocol.GetMessagesResponse(messages)
        elif method == 'InsertMessage':
            request = protocol.InsertMessageRequest.from_json(params)
            message_ts = int(time.time() * constants.MILLIS_PER_SEC)
            message = db_client.insert_message(
                    request.chat_id, 
                    request.user_id, 
                    request.message_text, 
                    message_ts)
            user = db_client.get_user(request.user_id)
            user = protocol.User(user.user_id, user.user_name)
            message = protocol.Message(
                    message.message_id,
                    message.chat_id,
                    user,
                    message.message_text,
                    message.message_ts)
            receivers = db_client.get_participants(request.chat_id)
            receiver_ids = [
                    receiver.user_id for receiver in receivers 
                    if receiver.user_id != request.user_id
            ]
            request = protocol.BroadcastRequest(receiver_ids, message)
            socket_lib.send_request(
                    'BroadcastRequest', 
                    request.to_json(), 
                    address=self._broadcast_address)
            response = protocol.InsertMessageResponse(message)
        else:
            # TODO(eugenhotaj): Return back a malformed request response.
            raise NotImplementedError()

        response = {'result': response.to_json(), 'id': id_}
        socket_lib.send_message(client_socket, json.dumps(response))


class BroadcastServer(Server):
    """A Server which handles streaming new conversations messages to users."""

    def __init__(self, address, max_workers=None):
        """Initializes a new BroadcastServer instance.

        Args: 
            address: See the base class.
            max_workers: See the base class.
        """
        super().__init__(address, max_workers=max_workers)
        self._socket_table = multiprocessing.Manager().dict()

    def handle_request(self, client_socket):
        """See the base class."""
        request = socket_lib.recv_message(client_socket)
        request = json.loads(request)
        method, params, id_ = request['method'], request['params'], request['id']

        keep_alive = False
        if method == 'OpenStreamRequest':
            request = protocol.OpenStreamRequest.from_json(params)
            self._socket_table[request.user_id] = client_socket
            response = protocol.OpenStreamResponse()
            keep_alive = True
        elif method == 'CloseStreamRequest':
            request = protocol.OpenStreamRequest.from_json(request)
            table_socket = self._socket_table[request.user_id]
            del self._socket_table[request.user_id]
            # If the client_socket is the same as the socket in the 
            # socket_table, defer closing it until we have send back a
            # response.
            if table_socket != client_socket:
                table_socket.close()
            response = protocol.CloseStreamResponse()
        elif method == 'BroadcastRequest':
            request = protocol.BroadcastRequest.from_json(params)
            for receiver_id in request.receiver_ids:
                if receiver_id in self._socket_table:
                    # TODO(eugenhoatj): Sending the BroadcastRequest to the 
                    # client doesn't really make sense.
                    response = {'jsonrpc': '2.0', 'result': request.to_json()}
                    socket_lib.send_message(self._socket_table[receiver_id], 
                                            json.dumps(response))
            response = protocol.BroadcastResponse()
        else:
            # TODO(eugenhotaj): Return back a malformed request response.
            raise NotImplementedError()

        response = {'result': response.to_json(), 'id': id_}
        socket_lib.send_message(client_socket, json.dumps(response))
        return keep_alive
