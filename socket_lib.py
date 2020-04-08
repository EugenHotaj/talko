"""Library which handles sending and receiving messages via sockets.

The server and clients communicate with each other via string messages. Each 
message contains a 10 byte header followed by a payload. The header is an 
integer indicating the size of the payload in bytes. The payload is a JSON 
encoded string. Messages are encoded to bytes via utf-8 encoding before being
transmitted over the wire.

The JSON messages contain the following fields. Note that user_id and user_name
correspond to the user that sent the message.
    message = {
        chat_id: 0123456789
        user_id: 9876543210
        user_name: 'TheOne'
        message_text: 'Hello, world!'
    }
"""

import collections
import errno
import json

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
    """Sends the message using the socket."""
    message = json.dumps(message)
    message = f'{len(message):<{HEADER_BYTES}}{message}'
    message = bytes(message, 'utf-8')
    socket.send(message)


def _recv_bytes(socket, n_bytes):
    """Receives n_bytes from the socket."""
    return socket.recv(n_bytes).decode('utf-8')


def recv_message(socket): 
    """Receives a full message from the socket."""
    message_size = int(_recv_bytes(socket, HEADER_BYTES))
    received_size = 0
    message = []
    while received_size < message_size:
        n_bytes = min(message_size - received_size, PACKET_BYTES)
        message.append(_recv_bytes(socket, n_bytes))
        received_size += n_bytes
    message = ''.join(message)
    return json.loads(message)


def recv_all_messages(socket):
    """Receives all unreceived messages from the socket."""
    messages = []
    while True:
        try:
            messages.append(recv_message(socket))
        except IOError as err:
            if err.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                break
    return messages
