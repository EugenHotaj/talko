"""Library which handles sending and receiving messages via sockets.

Messages are utf-8 encoded binary strings. Each message consists of a 10 byte
header followed by a payload. The header is an integer indicating the size of 
the payload in bytes. The payload consists of one, and only one, pickled Python
object defined in protocol.py. Because we control.
"""

import collections
import dataclasses
import errno

HEADER_BYTES = 10
PACKET_BYTES = 4096


def accept(socket, block=False):
    """Accepts a connection to the socket.

    Args:
        socket: The socket for which to accept connections.
        block: If True, blocks until a new connection is accepted.
    Returns: 
        Either a (socket, address_info) tuple if connected to a socket, or None.
    """
    while True:
        try:
            return socket.accept()
        except IOError as err: 
            if err.errno in (errno.EAGAIN, errno.EWOULDBLOCK) and not block:
                return


def send_message(socket, message):
    """Sends the string message using the socket."""
    message = f'{len(message):<{HEADER_BYTES}}{message}'
    message = bytes(message, 'utf-8')
    socket.send(message)


def _recv_bytes(socket, n_bytes):
    """Receives n_bytes from the socket and decodes them to utf-8 strings."""
    return socket.recv(n_bytes).decode('utf-8')


def recv_message(socket): 
    """Receives a full string message from the socket."""
    try:
        message_size = int(_recv_bytes(socket, HEADER_BYTES))
    except IOError as err:
        if err.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            return

    received_size = 0
    message = []
    while received_size < message_size:
        n_bytes = min(message_size - received_size, PACKET_BYTES)
        message.append(_recv_bytes(socket, n_bytes))
        received_size += n_bytes
    message = ''.join(message)
    return message


def recv_all_messages(socket):
    """Receives all pending messages from the socket."""
    messages = []
    while True:
        message = recv_message(socket)
        if not message:
            break
        messages.append(message)
    return messages
