"""Module containing the server.

See the 'socket_lib' module for the client-server communication protocol.

Currently, a separate process is created for each client.
"""

import argparse
import json
import multiprocessing
import socket
import time

import constants
import database_client 
import protocol
import socket_lib

# NOTE(eugenhotaj): We use processes instead of threads to get around the GIL.
MAX_WORKERS = 50


class Server:
    """A Server which can handle concurrent requests via process.

    Requests are processed via the handle_request() method which must be 
    overridden by the subclasses.
    """

    def __init__(self, address, is_blocking=True, max_workers=None):
        """Initializes a new Server instance.
        
        Args:
            address: The (host, port) tuple address to bind this server to.
            is_blocking: Whether to use a blocking socket.
            max_workers: The total number of workers to use for serving 
                requests. Requests which exceed the number of available workers
                are dropped.
        """
        self._address = address
        self._max_workers = max_workers or MAX_WORKERS

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self._socket.setblocking(is_blocking)

    def handle_request(self, client_socket):
        """Handles a request. Must be overridden by the subclass."""
        raise NotImplementedError()

    def _handle_request(self, client_socket, host, port):
        print(f'Connection from {host}:{port} established')
        try:
            self.handle_request(client_socket)
        finally:
            client_socket.close()
            print(f'Connection from {host}:{port} closed')

    def _keep_if_alive(self, worker):
        is_alive = worker.is_alive()
        if not is_alive:
            worker.close()
        return is_alive

    def serve_forever(self):
        """Serves requests indefinitely using a separate process per request."""
        self._socket.bind(self._address)
        self._socket.listen()

        workers = []
        while True:
            workers = [w for w in workers if self._keep_if_alive(w)]
            result = socket_lib.accept(self._socket)
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
                    # TODO(eugenhotaj): Start logging instead of using print.
                    print(f'WARNING: Connection from {host}:{port} shed')


class BroadcastServer(Server):
    """A Server which handles streaming chat conversations between users."""

    def __init__(self, address, dataserver_address, max_workers=None):
        """Initializes a new BroadcastServer instance.

        Args: 
            address: See the base class.
            dataserver_address: The address of the DataServer which handles 
                reading and writing chat data.
            max_workers: See the base class.
        """
        super().__init__(address, is_blocking=False, max_workers=max_workers)
        self._dataserver_address = dataserver_address
        self._socket_table = multiprocessing.Manager().dict()

    # TODO(eugenhotaj): Move this method to a shared library which can be used
    # by the client as well.
    def _send_request(self, method, params):
        """Sends a request and waits for a response from the server."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self._dataserver_address)
        request = {'method': method, 'params': params.to_json(), 'id': 0}
        socket_lib.send_message(sock, json.dumps(request))
        response = socket_lib.recv_message(sock)
        sock.close()
        return json.loads(response)['result']

    def handle_request(self, client_socket):
        """Handles requests from the client_socket."""
        user_id = None
        while True:
            try: 
                raw_requests = socket_lib.recv_all_messages(client_socket)
            except:
                # Remove our socket from the socket_table if disconnected.
                if user_id in self._socket_table:
                    del self._socket_table[user_id]
                raise

            # Parse raw requests into request objects.
            requests = []
            for request in raw_requests:
                request = json.loads(request)['params']
                request = protocol.BroadcastRequest.from_json(request)
                requests.append(request)

            # TODO(eugenhotaj): We may want to generate the timestamp per 
            # message if we need more granualarity.
            message_ts = int(time.time() * constants.MILLIS_PER_SEC)
            for request in requests:
                if not user_id:
                    user_id = request.user_id
                    self._socket_table[user_id] = client_socket
                assert user_id == request.user_id

                # First, insert the new message into the database then broadcast
                # it out to all participants that are online.
                req = protocol.InsertMessageRequest(
                        request.chat_id, user_id, request.message_text, 
                        message_ts)
                self._send_request('InsertMessage', req)
                req = protocol.GetParticipantsRequest(request.chat_id)
                resp = self._send_request('GetParticipants', req)
                resp = protocol.GetParticipantsResponse(resp)
                for user in resp.users:
                    if (user.user_id != user_id and
                        user.user_id in self._socket_table):
                        socket_lib.send_message(
                                self._socket_table[receiver.user_id], 
                                request.to_json())


class DataServer(Server):
    """A Server which handles reading and writing chat data.

    Unlike the BroadcastServer, the DataServer operates via a request/response
    protocol. This means that it handles exactly one request per client 
    connection and responds back with exactly one response, after which the 
    connection to the client socket is terminated.

    If the client sends multiple requests on the same socket, only the first
    request is processed and subsequent requests are ignored.
    """

    def __init__(self, address, db_path, max_workers=None):
        """Initializes a new DataServer instance.

        Args:
            address: See the base class.
            db_path: The path to the SQLite chat database.
        """
        super().__init__(address, is_blocking=False, max_workers=max_workers)
        self._db_path = db_path

    def handle_request(self, client_socket):
        """Handles requests from the client_socket."""
        db_client = database_client.DatabaseClient(self._db_path)
        request = socket_lib.recv_message(client_socket)
        request = json.loads(request)
        method, params, id_ = request['method'], request['params'], request['id']

        if method == 'InsertUser':
            request = protocol.InsertUserRequest.from_json(params)
            user_id = db_client.insert_user(request.user_name)
            response = protocol.InsertUserResponse(user_id)
        elif method == 'GetChats':
            request = protocol.GetChatsRequest.from_json(params)
            chats = db_client.get_chats(request.user_id)
            response = protocol.GetChatsResponse(chats)
        elif method == 'InsertChat':
            request = protocol.InsertChatRequest.from_json(params)
            user_ids = request.user_ids
            chat_id = None
            if len(user_ids) == 2:
                chat_id = db_client.get_private_chat_id(*user_ids)
            if not chat_id:
                chat_id = db_client.insert_chat(request.chat_name, user_ids)
            response = protocol.InsertChatResponse(chat_id)
        elif method == 'GetParticipants':
            request = protocol.GetParticipantsRequest.from_json(params)
            users = db_client.get_participants(request.chat_id)
            response = protocol.GetParticipantsResponse(users)
        elif method == 'GetMessages':
            request = protocol.GetMessagesRequest.from_json(params)
            messages = db_client.get_messages(request.chat_id)
            response = protocol.GetMessagesResponse(messages)
        elif method == 'InsertMessage':
            request = protocol.InsertMessageRequest.from_json(params)
            message_id = db_client.insert_message(
                    request.chat_id, 
                    request.user_id, 
                    request.message_text, 
                    request.message_timestamp)
            response = protocol.InsertMessageResponse(message_id)
        else:
            # TODO(eugenhotaj): Return back a malformed request response.
            raise NotImplementedError()

        response = { 'result': response.to_json(), 'id': id_}
        socket_lib.send_message(client_socket, json.dumps(response))


if __name__ == '__main__':
    # Parse flags.
    parser = argparse.ArgumentParser()
    parser.add_argument('--db_path', type=str, required=True, 
                        help='Path to the SQLite chat database')
    FLAGS = parser.parse_args()

    db_path = FLAGS.db_path
    broadcastserver_address = (constants.LOCALHOST, constants.BROADCAST_PORT)
    dataserver_address = (constants.LOCALHOST, constants.DATA_PORT)
 
    def start_broadcast_server():
        server = BroadcastServer(broadcastserver_address, dataserver_address)
        server.serve_forever()

    def start_data_server():
        server = DataServer(dataserver_address, db_path)
        server.serve_forever()

    multiprocessing.Process(target=start_data_server).start()
    multiprocessing.Process(target=start_broadcast_server).start()
