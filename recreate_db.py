"""Script to drop the database and recreates it, erasing all stored data."""

import argparse
import os
import sqlite3


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', type=str, required=True, 
                        help='Path to the SQLite database file.')
    FLAGS = parser.parse_args()

    assert FLAGS.path, 'path cannot be empty'

    if os.path.exists(FLAGS.path):
        os.remove(FLAGS.path)
    connection = sqlite3.connect(FLAGS.path)
    sql = open('recreate_db.sql', 'r').read()
    with connection:
        connection.executescript(sql)
