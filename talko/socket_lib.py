"""Library which handles sending and receiving messages via sockets.

Messages are utf-8 encoded binary strings. Each message consists of a 10 byte
header followed by a payload. The header is an integer indicating the size of 
the payload in bytes. The payload consists of one, and only one, pickled Python
object defined in protocol.py. Because we control.
"""

import collections
import dataclasses
import errno
import json
import socket 
import uuid

HEADER_BYTES = 10
PACKET_BYTES = 4096


def send_message(sock, message):
    """Sends the string message using the socket."""
    message = f'{len(message):<{HEADER_BYTES}}{message}'
    message = bytes(message, 'utf-8')
    sock.send(message)


def _recv_bytes(sock, n_bytes):
    """Receives n_bytes from the socket and decodes them to utf-8 strings."""
    return sock.recv(n_bytes).decode('utf-8')


def recv_message(sock): 
    """Receives a full string message from the socket."""
    message_size = int(_recv_bytes(sock, HEADER_BYTES))
    received_size = 0
    message = []
    while received_size < message_size:
        n_bytes = min(message_size - received_size, PACKET_BYTES)
        message.append(_recv_bytes(sock, n_bytes))
        received_size += n_bytes
    message = ''.join(message)
    return message


def send_request(
        method, 
        params, 
        sock=None,
        address=None, 
        keep_alive=False):
    """Sends a JSON-RPC request to the given address.

    Args:
        method: The RPC method name.
        params: The RPC method parameters.
        sock: The socket to use for sending the request and receiving the
            response. If 'None', the 'address' field must be given.        
        address: The (host, port) tuple address where to send the request and
            receive the response. Must be 'None' if a 'sock' is provided.
        keep_alive: If True, does not close the socket before returning. Setting
            this to 'True' is only meaningful if a 'sock' is provided.
    Returns:
        The response or 'None'.
    """
    if bool(sock) == bool(address):
        raise ValueError(
                "One, and only one, 'sock' or 'address' must be provided.")
    if not sock:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(address)

    request = {
            'jsonrpc': '2.0', 
            'method': method, 
            'params': params, 
            'id': uuid.uuid4().int
    }
    send_message(sock, json.dumps(request))
    response = json.loads(recv_message(sock))
    assert request['id'] == response['id']

    if not keep_alive:
        sock.close()
    # TODO(eugenhotaj): We can't assume that the response succeeded here. 
    # We also need to handle response['error'] correctly.
    return response['result']
