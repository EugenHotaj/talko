"""Module containing the server.

See the 'socket_lib' module for the client-server communication protocol.

Currently, a separate process is created for each client.
"""

import argparse
import multiprocessing
import socket
import time

import constants
import database_lib
import socket_lib

CONNECTION_BACKLOG = 3
# NOTE(eugenhotaj): We use processes instead of threads to get around the GIL.
MAX_WORKERS = 10

class Client:
    """A data cotainer which wraps client connections."""
    
    def __init__(self, socket, address_info):
        self.socket = socket
        address, port = address_info
        self.address = f'{address}:{port}'


class Worker(multiprocessing.Process):
    """A worker process which handles a single client."""

    def __init__(self, client, client_table, db_path):
        """Initializes a new Worker instance.
        
        Args:
            client: The Client this worker is handling.
            client_table: Table holding all clients connections to the server.
            db_path: The path to the SQLite database.
        """
        super().__init__()
        self.client = client
        self._client_table = client_table
        self._db_path = db_path 

        # These values are set at process runtime.
        self._user_id = None
        self._database = None

    def run(self):
        while True:
            if not self._database:
                self._database = database_lib.Database(self._db_path)

            try: 
                messages = socket_lib.recv_all_messages(self.client.socket)
            finally:
                # Remove our client from client_table if the socket disconnects.
                if self._user_id in self._client_table:
                    del self._client_table[self._user_id]
                break
            # TODO(eugenhotaj): We may want to generate the timestamp per 
            # message if we need more granualarity.
            ts = int(time.time() * MILLIS_PER_SEC)
            for message in messages:
                user_id = message['user_id']
                if not self._user_id:
                    self._user_id = user_id 
                    self._client_table[user_id] = self.client
                assert user_id == self._user_id

                chat_id = message['chat_id']
                message_text = message['message_text']
                # First, insert the new message into the database.
                self._database.insert_message(
                        chat_id, user_id, message_text, ts)
                # Then, send the message to all active receivers.
                chat = self._database.get_chat(chat_id)
                receivers = [
                        receiver for receiver in chat.user_ids
                        if receiver != user_id and receiver in self._client_table
                ]
                for receiver in receivers:
                    socket_lib.send_message(
                            self._client_table[receiver].socket, message)


def _keep_if_alive(process):
    """Keeps a process if it is alive, otherwise closes it."""
    is_alive = process.is_alive()
    if not is_alive:
        process.close()
        print(f'Connection from {process.client.address} closed')
    return is_alive


def serve_forever(db_path):
    """Serves client sockets forever."""
    # Set up the server socket.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setblocking(False)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    server_socket.bind((constants.LOCALHOST, constants.LOCALHOST_PORT))
    server_socket.listen(CONNECTION_BACKLOG)

    # Holds client connections in shared memory across workers.
    client_table = multiprocessing.Manager().dict()

    workers = []
    while True:
        result = socket_lib.accept(server_socket)
        if result is None:
            continue

        client_socket, address_info = result
        workers = [worker for worker in workers if _keep_if_alive(worker)]
        if len(workers) <MAX_WORKERS:
            client = Client(client_socket, address_info)
            worker = Worker(client, client_table, FLAGS.db_path)
            worker.start()
            workers.append(worker)
            print(f'Connection from {client.address} established')
        else:
            # If the server is overloaded, shed any new connections.
            socket.shutdown(socket.SHUT_RDWR)
            socket.close()
            print(f'Connection from {client.address} shed: server overloaded')


if __name__ == '__main__':
    # Parse flags.
    parser = argparse.ArgumentParser()
    parser.add_argument('--db_path', type=str, required=True, 
                        help='Path to the SQLite chat database')
    FLAGS = parser.parse_args()
    serve_forever(FLAGS.db_path)
