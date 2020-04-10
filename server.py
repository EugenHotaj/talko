"""Module containing the server.

See the 'socket_lib' module for the client-server communication protocol.

Currently, a separate process is created for each client.
"""

import argparse
import multiprocessing
import socket
import time

import constants
import database_client 
import socket_lib

# NOTE(eugenhotaj): We use processes instead of threads to get around the GIL.
MAX_WORKERS = 10


class Server:
    """A Server which can handle concurrent requests via process.

    Requests are processed via the handle_request() method which must be 
    overridden by the subclasses.
    """

    def __init__(self, host, port, db_path, max_workers=MAX_WORKERS):
        """Initializes a new Server instance.
        
        Args:
            host: The host address from which to serve requests.
            port: The port from which to serve requests.
            db_path: A path to the SQLite database.
            max_workers: The total number of workers to use for serving 
                requests. Requests which exceed the number of available workers
                are dropped.
        """
        self._address = (host, port)
        self._db_path = db_path
        self._max_workers = max_workers 

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self._socket.setblocking(False)

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
    """A Server which handles broadcasting chat conversations between users."""

    def __init__(self, host, port, db_path, max_workers=MAX_WORKERS):
        super().__init__(host, port, db_path, max_workers)
        self._socket_table = multiprocessing.Manager().dict()

    def handle_request(self, client_socket):
        """Handles requests from the client_socket.

        The server receives real-time conversation messages from the 
        client_socket which it first stores in the SQLite database then 
        broadcasts to the intended recipiants.
        """
        user_id = None
        db_client = database_client.DatabaseClient(self._db_path)
        while True:
            try: 
                messages = socket_lib.recv_all_messages(client_socket)
            except:
                # Remove our socket from the socket_table if disconnected.
                if user_id in self._socket_table:
                    del self._socket_table[user_id]
                raise

            # TODO(eugenhotaj): We may want to generate the timestamp per 
            # message if we need more granualarity.
            message_ts = int(time.time() * constants.MILLIS_PER_SEC)
            for message in messages:
                if not user_id:
                    user_id = message['user_id']
                    self._socket_table[user_id] = client_socket
                assert user_id == message['user_id']

                chat_id = message['chat_id']
                message_text = message['message_text']
                # First, insert the new message into the database then send
                # it out to all participants that are online.
                db_client.insert_message(
                        chat_id, user_id, message_text, message_ts)
                participants = db_client.get_participants(chat_id)
                receivers = [
                        user for user in participants 
                        if user.user_id != user_id and 
                        user.user_id in self._socket_table
                ]
                for receiver in receivers:
                    socket_lib.send_message(
                            self._socket_table[receiver.user_id], message)


if __name__ == '__main__':
    # Parse flags.
    parser = argparse.ArgumentParser()
    parser.add_argument('--db_path', type=str, required=True, 
                        help='Path to the SQLite chat database')
    FLAGS = parser.parse_args()

    broadcast_server = BroadcastServer(
            constants.LOCALHOST, constants.LOCALHOST_PORT,  FLAGS.db_path)
    broadcast_server.serve_forever()
