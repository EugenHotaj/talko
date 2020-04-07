"""Module which provides communication with the database."""

import sqlite3


class Database:
    """Object which abstracts away and handles database communications."""

    def __init__(self, db_path):
        """Initializes a new Database instance.

        Args:
            db_path: The path to the SQLite database.
        """
        self._connection = sqlite3.connect(db_path)

    def get_user(self, user_id):
        """Returns the user with user_id."""
        with self._connection:
            result = self._connection.execute(
                    "SELECT * FROM Users WHERE user_id=?", (user_id,))
        return result.fetchone()

    def insert_user(self, user_id, user_name):
        """Inserts a new user into the Users table."""
        with self._connection:
            self._connection.execute(
                    "INSERT INTO Users(user_id, user_name) VALUES(?, ?)",
                    (user_id, user_name))
        return (user_id, user_name)

    def list_chats(self, user_id):
        """Returns all chats the user is participating in."""
        with self._connection:
            result = self._connection.execute(
                    "SELECT * FROM Chats WHERE user1_id=? OR user2_id=?", 
                    (user_id, user_id))
        return result.fetchall()

    def get_chat_id_for_user_ids(self, user1_id, user2_id):
        """Returns the id of the chat between the given users."""
        user_ids = tuple(sorted((user1_id, user2_id)))
        with self._connection:
            result = self._connection.execute(
                    "SELECT chat_id FROM Chats WHERE user1_id=? AND user2_id=?", 
                    user_ids)
        return result.fetchone()

    def insert_chat(self, user1_id, user2_id):
        """Inserts a new chat between the two users.

        The user_ids are sorted so that user1 is always the user with the lower
        user_id.
        """
        user_ids = tuple(sorted((user1_id, user2_id)))
        with self._connection:
            result = self._connection.execute(
                    "INSERT INTO Chats(user1_id, user2_id) VALUES(?, ?)",
                    user_ids)
        return result.lastrowid

    def list_messages(self, chat_id):
        """Returns all messages for the chat."""
        with self._connection:
            result = self._connection.execute(
                    "SELECT * FROM Messages WHERE chat_id=?", (chat_id))
        return result.fetchall()
