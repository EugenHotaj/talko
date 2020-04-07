"""Module containing the server.

See the 'socket_lib' module for the client-server communication protocol.

Currently, a separate process is created for each client.
"""

import collections
import multiprocessing
import socket

import constants
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

    def __init__(self, client, client_table, client_db):
        """Initializes a new Worker instance.
        
        Args:
            client: The Client this worker is handling.
            client_table: Table holding all clients connections to the server.
            client_db: Table holding chat data.
        """
        super().__init__()
        self._client = client
        self._client_table = client_table
        self._client_id = None

    def run(self):
        while True:
            # Route all messages from the sender to the receiver.
            messages = socket_lib.recv_all_messages(self._client.socket)
            for message in messages:
                sender = message['sender']
                if not self._client_id:
                    self._client_id = sender
                    self._client_table[sender] = self._client
                assert sender == self._client_id
                receiver, text = message['receiver'], message['text']
                message = {
                    'sender': sender, 'receiver': receiver, 'text': text
                }
                # TODO(eugenhotaj): Store messages if receiver is not online.
                if receiver in self._client_table:
                    socket_lib.send_message(
                            self._client_table[receiver].socket, message)

        # Remove the client from the client_table once the connection is over.
        del self._client_table[self._client_id]


def _keep_if_alive(process):
    """Keeps a process if it is alive, otherwise closes it."""
    if not process.is_alive():
        process.close()
        print(f'Connection from {process.address}:{process.port} closed')
    return process.is_alive()


if __name__ == '__main__':
    # Set up the server socket.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setblocking(False)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    server_socket.bind((constants.LOCALHOST, constants.LOCALHOST_PORT))
    server_socket.listen(CONNECTION_BACKLOG)

    # Holds client data in shared memory across workers.
    client_manager = multiprocessing.Manager()
    client_table = client_manager.dict()
    # TODO(eugenhotaj): Use an actual database here instead of storing things
    # in memory.
    client_db = client_manager.dict()

    workers = []

    while True:
        workers = [worker for worker in workers if _keep_if_alive(worker)]

        client = Client(*socket_lib.accept(server_socket, block=True))
        print(f'Connection from {client.address} established')

        # If the server is overloaded, start shedding new connections.
        if len(workers) >= MAX_WORKERS:
            print(f'Connection from {client.address} shed: server overloaded')
            client.socket.shutdown(socket.SHUT_RDWR)
            client.socket.close()

        worker = Worker(client, client_table)
        worker.start()
        workers.append(worker)
