"""Defines constants shared across the server and the client."""

import socket

HEADER_BYTES = 10
LOCALHOST = socket.gethostname()
BROADCAST_PORT = 8888
DATA_PORT = 8889
MILLIS_PER_SEC = 1000
