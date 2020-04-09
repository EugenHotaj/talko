"""Script to drop the database and recreates it, erasing all stored data."""

import argparse
import os
import sqlite3


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db_path', type=str, required=True, 
                        help='Path to the SQLite database.')
    FLAGS = parser.parse_args()

    assert FLAGS.db_path, '--db_path cannot be empty'

    if os.path.exists(FLAGS.db_path):
        os.remove(FLAGS.db_path)
    connection = sqlite3.connect(FLAGS.db_path)
    sql = open('schema.sql', 'r').read()
    with connection:
        connection.executescript(sql)
