"""Definitions of the BroadcastServer and DataServer."""

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
    """A Server which can handle concurrent requests via processes.

    Requests are processed via the handle_request() method which must be 
    overridden by the subclasses.
    """

    def __init__(self, name, address, max_workers=None):
        """Initializes a new Server instance.
        
        Args:
            name: The name of the server.
            address: The (host, port) tuple address to bind this server to.
            max_workers: The total number of workers to use for serving 
                requests. Requests which exceed the number of available workers
                are dropped.
        """
        self._name = name
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
        print(f'{self._name}: Connection from {host}:{port} established')
        try:
            keep_alive = self.handle_request(client_socket)
            if not keep_alive:
                client_socket.close()
                print(f'{self._name}: Connection from {host}:{port} closed')
        except Exception:
            client_socket.close()
            print(f'{self._name}: Connection from {host}:{port} interrupted')
            raise

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
            result = self._socket.accept()
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
                    print(f'{self._name}: [WARNING] Connection from {host}:{port} shed')


class BroadcastServer(Server):
    """A Server which handles streaming new conversations messages to users."""

    def __init__(self, address, max_workers=None):
        """Initializes a new BroadcastServer instance.

        Args: 
            address: See the base class.
            max_workers: See the base class.
        """
        super().__init__('BroadcastServer', address, max_workers=max_workers)
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
        super().__init__('DataServer', address, max_workers=max_workers)
        self._broadcast_address = broadcast_address
        self._db_path = db_path

    def handle_request(self, client_socket):
        """See the base class."""
        db_client = database_client.DatabaseClient(self._db_path)
        request = socket_lib.recv_message(client_socket)
        request = json.loads(request)
        method, params, id_ = request['method'], request['params'], request['id']

        if method == 'InsertUser':
            request = protocol.InsertUserRequest.from_json(params)
            user = db_client.insert_user(request.user_name)
            response = protocol.InsertUserResponse(user)
        elif method == 'GetChats':
            request = protocol.GetChatsRequest.from_json(params)
            chats = db_client.get_chats(request.user_id)
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
            request = protocol.GetMessagesRequest.from_json(params)
            messages = db_client.get_messages(request.chat_id)
            response = protocol.GetMessagesResponse(messages)
        elif method == 'InsertMessage':
            request = protocol.InsertMessageRequest.from_json(params)
            message_ts = int(time.time() * constants.MILLIS_PER_SEC)
            message = db_client.insert_message(
                    request.chat_id, 
                    request.user_id, 
                    request.message_text, 
                    message_ts)
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
        server = BroadcastServer(broadcastserver_address)
        server.serve_forever()

    def start_data_server():
        server = DataServer(dataserver_address, broadcastserver_address, db_path)
        server.serve_forever()

    multiprocessing.Process(target=start_data_server).start()
    multiprocessing.Process(target=start_broadcast_server).start()
