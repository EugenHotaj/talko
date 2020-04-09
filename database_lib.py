"""Module which provides communication with the database."""

import collections
from dataclasses import dataclass
from typing import List
import sqlite3


@dataclass(frozen=True)
class User:
    """Data container for Users."""
    user_id: int
    user_name: str


@dataclass(frozen=True)
class Chat:
    """Data container for Chats."""
    chat_id: int
    chat_name: str


@dataclass(frozen=True)
class Message:
    """Data container for Messages."""
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
        query = "SELECT * FROM Users WHERE user_id=?"
        with self._connection:
            cursor = self._connection.execute(query, (user_id,))
        row = cursor.fetchone()
        return User(*row) if row else None

    # TODO(eugenhotaj): Should we take in a User instance here?
    def insert_user(self, user_id, user_name):
        """Inserts a new user into the Users table."""
        query = "INSERT INTO Users (user_id, user_name) VALUES (?, ?)"
        with self._connection:
            self._connection.execute(query, (user_id, user_name))
        return user_id

    def list_user_chats(self, user_id):
        """Returns all chats the user is participating in."""
        query = """SELECT Chats.chat_id, chat_name 
                   FROM Chats JOIN Participants
                     ON Chats.chat_id = Participants.chat_id
                   WHERE user_id=?"""
        with self._connection:
            cursor = self._connection.execute(query, (user_id,))
        return [Chat(*row) for row in cursor.fetchall()]

    def get_chat_users(self, chat_id):
        """Returns all users in the chat with given chat_id."""
        query = """SELECT Users.user_id, user_name 
                   FROM Users JOIN Participants 
                     ON Users.user_id = Participants.user_id
                   WHERE chat_id=?"""
        with self._connection:
            cursor = self._connection.execute(query, (chat_id,))
        return [User(*row) for row in cursor.fetchall()]

    def get_private_chat_id(self, user1_id, user2_id):
        """Returns the id of the private chat between the given users.

        N.B. This is a complex, expensive query. Use with care.
        """
        query = """SELECT chat_id, user_ids
                   FROM (
                     SELECT chat_id, group_concat(user_id) as user_ids
                     FROM Participants
                     GROUP BY user_id)
                   WHERE ? IN user_ids OR ? in user_ids)"""
        with self._connection:
            cursor = self._connection.execute(query (user1_id, user2_id))
        chat_ids = [
                chat_id for chat_id, user_ids in cursor.fetchall() 
                if len(user_ids) == 2
        ]
        assert len(chat_ids) <= 1
        return chat_ids[0] if chat_ids else None

    # TODO(eugenhotaj): Should we take in a Chat instance here and check that
    # chat_id == None? We then return a new Chat with chat_id = 
    # cursor.lastrowid.
    def insert_chat(self, chat_name, user_ids):
        """Inserts a new chat with the given user_ids as participants."""
        query = "INSERT INTO Chats (chat_name) VALUES (?)"
        with self._connection:
            cursor = self._connection.execute(query, (chat_name,))

        # Inserting the participants does not need to happen in the same
        # transaction as inserting the chat.
        chat_id = cursor.lastrowid
        participants = [(chat_id, user_id) for user_id in user_ids]
        query = "INSERT INTO Participants (chat_id, user_id) VALUES (?, ?)"
        with self._connection:
            self._connection.executemany(query, participants)

        return chat_id

    def list_messages(self, chat_id):
        """Returns all messages for the chat with given chat_id."""
        query = "SELECT * FROM Messages WHERE chat_id=? ORDER_BY message_ts"
        with self._connection:
            cursor = self._connection.execute(query, (chat_id,))
        return [Message(*row) for row in cursor.fetchall()]

    # TODO(eugenhotaj): Should we take in a Message instance here and check that
    # message_id == None? We then return a new Message with message_id = 
    # cursor.lastrowid.
    def insert_message(self, chat_id, user_id, message_text, message_ts):
        """Inserts a new message."""
        query = """INSERT INTO Messages 
                     (chat_id, user_id, message_text, message_ts)
                   VALUES (?, ?, ?, ?)"""
        with self._connection:
            cursor = self._connection.execute(
                    query, (chat_id, user_id, message_text, message_ts))
        return cursor.lastrowid
