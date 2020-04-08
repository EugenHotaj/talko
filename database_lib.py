"""Module which provides communication with the database."""

import collections
from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class User:
    """Maps to a User row in the database."""
    user_id: int
    user_name: str


@dataclass(frozen=True)
class Chat:
    """Maps to a Chat row in the database."""
    chat_id: int
    user1_id: int
    user2_id: int

    @property
    def user_ids(self):
        """Returns all user_ids as a list."""
        return [self.user1_id, self.user2_id]


@dataclass(frozen=True)
class Message:
    """Maps to a Chat row in the database."""
    message_id: int
    chat_id: int
    user_id: int
    message_text: str
    message_ts: int


class Database:
    """A client which handles communications with the database."""

    def __init__(self, db_path):
        """Initializes a new Database instance.

        Args:
            db_path: The path to the SQLite database.
        """
        self._path = db_path
        self._connection = sqlite3.connect(db_path)

    def get_user(self, user_id):
        """Returns the user with given user_id."""
        cursor = self._connection.execute(
                "SELECT * FROM Users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        return User(*row) if row else None


    # TODO(eugenhotaj): Should we take in a User instance here?
    def insert_user(self, user_id, user_name):
        """Inserts a new user into the Users table."""
        with self._connection:
            self._connection.execute(
                    "INSERT INTO Users(user_id, user_name) VALUES(?, ?)",
                    (user_id, user_name))
        return user_id

    def list_chats(self, user_id):
        """Returns all chats the user is participating in."""
        with self._connection:
            cursor = self._connection.execute(
                    "SELECT * FROM Chats WHERE user1_id=? OR user2_id=?", 
                    (user_id, user_id))
        return [Chat(*row) for row in cursor.fetchall()]

    def get_chat(self, chat_id):
        """Returns the chat with given chat_id."""
        with self._connection:
            cursor = self._connection.execute(
                    "SELECT * FROM Chats WHERE chat_id=?", (chat_id,))
        row = cursor.fetchone()
        return Chat(*row) if row else None

    def get_chat_id_for_user_ids(self, user1_id, user2_id):
        """Returns the id of the chat between the given users."""
        user_ids = tuple(sorted((user1_id, user2_id)))
        with self._connection:
            cursor = self._connection.execute(
                    "SELECT chat_id FROM Chats WHERE user1_id=? AND user2_id=?", 
                    user_ids)
        row = cursor.fetchone()
        return row[0] if row else None

    # TODO(eugenhotaj): Should we take in a Chat instance here and check that
    # chat_id == None? We then return a new Chat with chat_id = 
    # cursor.lastrowid.
    def insert_chat(self, user1_id, user2_id):
        """Inserts a new chat between the two users.

        The user_ids are sorted so that user1 is always the user with the lower
        user_id.
        """
        user_ids = tuple(sorted((user1_id, user2_id)))
        with self._connection:
            cursor = self._connection.execute(
                    "INSERT INTO Chats(user1_id, user2_id) VALUES(?, ?)",
                    user_ids)
        return cursor.lastrowid

    def list_messages(self, chat_id):
        """Returns all messages for the chat."""
        with self._connection:
            cursor = self._connection.execute(
                    """SELECT * FROM Messages 
                       WHERE chat_id=? 
                       ORDER BY message_ts""", 
                    (chat_id,))
        return [Message(*row) for row in cursor.fetchall()]

    # TODO(eugenhotaj): Should we take in a Message instance here and check that
    # message_id == None? We then return a new Message with message_id = 
    # cursor.lastrowid.
    def insert_message(self, chat_id, user_id, message_text, message_ts):
        """Inserts a new message."""
        with self._connection:
            cursor = self._connection.execute(
                    """INSERT INTO 
                           Messages(chat_id, user_id, message_text, message_ts)
                       VALUES(?, ?, ?, ?)""",
                    (chat_id, user_id, message_text, message_ts))
        return cursor.lastrowid
