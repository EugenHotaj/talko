"""A script which starts the chat servers and creates a new Curses UI client.

Calling the script multiple times in a row creates multiple clients but reuses
the servers if they're already running.
"""

import argparse 
import multiprocessing
import socket
import time

from talko import constants
from talko import database_client
from talko import server
from talko.ui import curses_ui


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
    parser.add_argument('--user_id', type=int, required=True, 
                        help='Id for the connected user')
    parser.add_argument('--db_path', type=str, required=True, 
                        help='Path to the SQLite chat database')
    parser.add_argument(
            '--recreate_db', type=bool, required=False, default=False, 
            help=('Whether to drop and recreate the SQLite chat database if it ' 
                  'exists'))
    FLAGS = parser.parse_args()

    user_id = FLAGS.user_id
    db_path = FLAGS.db_path
    recreate_db = FLAGS.recreate_db
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
        time.sleep(.001)  # Wait a bit for the servers to start up.

    # Create a new client.
    curses_ui.main(user_id, data_address, broadcast_address)
