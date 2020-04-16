"""A script which starts the chat servers and creates a new UI client.

The UI client type is specified by the '--ui_client' flag and must be either
a 'terminal' (i.e. ncurses) client or a 'webapp' (i.e. Flask app).

Calling the script multiple times with '--ui_client=terminal' creates multiple
terminal clients.
"""

import argparse 
import multiprocessing
import os
import socket
import time

from talko import constants
from talko import database_client
from talko import server
from talko.ui import curses_ui
from talko.ui.web_app import app


def _check_socket(address):
    """Returns whether a socket is already bound to the given address."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        sock.bind(address)
        return False
    except OSError:
        return True
    finally:
        sock.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui_client', type=str, required=True,
                        choices=['terminal', 'webapp'],
                        help='The type of UI client to create')
    parser.add_argument(
            '--terminal_user_id', type=int, required=False, 
            help='The user_id to connect as if creating a terminal client')
    parser.add_argument('--db_path', type=str, required=True, 
                        help='Path to the SQLite chat database')
    parser.add_argument(
            '--recreate_db', type=bool, required=False, default=False, 
            help=('Drop and recreate the SQLite chat database if it exists'))

    FLAGS = parser.parse_args()
    ui_client = FLAGS.ui_client
    user_id = FLAGS.terminal_user_id
    db_path = FLAGS.db_path
    recreate_db = FLAGS.recreate_db

    if ui_client == 'terminal' and user_id is None:
        raise ValueError(
                '--terminal_user_id is required when --ui_client=terminal')

    data_address = (constants.LOCALHOST, constants.DATA_PORT)
    broadcast_address = (constants.LOCALHOST, constants.BROADCAST_PORT)

    def start_data_server():
        data_server = server.DataServer(data_address, broadcast_address, db_path)
        data_server.serve_forever()

    def start_broadcast_server():
        broadcast_server = server.BroadcastServer(broadcast_address)
        broadcast_server.serve_forever()

    # (Re)create the chat database if necessary.
    database_client.create_database(db_path, overwrite=recreate_db)

    # Only start the servers if they're not already running.
    if not _check_socket(data_address) and not _check_socket(broadcast_address):
        multiprocessing.Process(target=start_data_server).start()
        multiprocessing.Process(target=start_broadcast_server).start()
        time.sleep(.05)  # Wait a bit for the servers to start up.

    # Create a new client.
    if ui_client == 'terminal':
        curses_ui.main(user_id, data_address, broadcast_address)
    else:
        app.main(data_address, broadcast_address)
