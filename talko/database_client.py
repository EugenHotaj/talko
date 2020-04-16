"""Module which provides communication with the database."""

import dataclasses
import os
import sqlite3


@dataclasses.dataclass
class User:
    user_id: int
    user_name: str


@dataclasses.dataclass
class Chat:
    chat_id: int
    chat_name: str


@dataclasses.dataclass
class Participant:
    participant_id: int
    chat_id: int
    user_id: int


@dataclasses.dataclass
class Message:
    message_id: int
    chat_id: int
    user_id: int
    message_text: str
    message_ts: int


def create_database(db_path, overwrite=False):
    """Creates a new database at the given db_path.

    If db_path already exists and overwrite=True, the existing database will
    be dropped and recreated. All previous data will be lost.
    """
    if os.path.exists(db_path):
        if not overwrite:
            return
        os.remove(db_path)
    sql = open('schema.sql', 'r').read()
    connection = sqlite3.connect(db_path)
    with connection:
        connection.executescript(sql)


class DatabaseClient:
    """A client which handles communications with the database."""

    def __init__(self, db_path):
        """Initializes a new DatabaseClient instance.

        Args:
            db_path: The path to the SQLite database.
        """
        self._path = db_path
        self._connection = sqlite3.connect(db_path)

    def get_user(self, user_id):
        """Returns the users with the given user_ids."""
        query = f'SELECT * FROM Users WHERE user_id = ?'
        with self._connection:
            cursor = self._connection.execute(query, user_id)
        return User(*cursor.fetchone())

    # TODO(eugenhotaj): Should we take in a User instance here?
    def insert_user(self, user_name):
        """Inserts a new user into the Users table."""
        query = 'INSERT INTO Users (user_id, user_name) VALUES (?, ?)'
        with self._connection:
            cursor = self._connection.execute(query, (user_id, user_name))
        return User(cursor.lastrowid, user_name)

    def get_chats(self, user_id):
        """Returns all chats the user is participating in."""
        query = """SELECT Chats.chat_id, chat_name 
            FROM Chats JOIN Participants ON Chats.chat_id = Participants.chat_id
            WHERE user_id = ?"""
        with self._connection:
            cursor = self._connection.execute(query, (user_id,))
        return [Chat(*row) for row in cursor.fetchall()]

    def get_participants(self, chat_id):
        """Returns all users participating in the chat with given chat_id."""
        query = """SELECT Users.user_id, user_name 
            FROM Users JOIN Participants ON Users.user_id = Participants.user_id
            WHERE chat_id = ?"""
        with self._connection:
            cursor = self._connection.execute(query, (chat_id,))
        return [User(*row) for row in cursor.fetchall()]

    def get_private_chat_id(self, user1_id, user2_id):
        """Returns the id of the private chat between the given users."""
        query = f"""SELECT Participants.chat_id, user_id 
            FROM Participants JOIN  Chats ON Participants.chat_id = Chats.chat_id
            WHERE is_private = True AND user_id IN (?, ?)"""
        with self._connection:
            cursor = self._connection.execute(query, (user1_id, user2_id))
        user_to_chats = {user1_id: set(), user2_id: set()}
        for chat_id, user_id in cursor.fetchall():
            user_to_chats[user_id].add(chat_id)
        private_chat = list(user_to_chats[0] & user_to_chats[1])
        assert len(private_chat) <= 1
        return private_chat[0] if private_chat else None

    # TODO(eugenhotaj): Should we take in a Chat instance here and check that
    # chat_id == None? We then return a new Chat with chat_id = 
    # cursor.lastrowid.
    def insert_chat(self, chat_name, user_ids):
        """Inserts a new chat with the given user_ids as participants."""
        query = 'INSERT INTO Chats (chat_name, is_private) VALUES (?, ?)'
        is_private = len(user_ids) == 2
        with self._connection:
            cursor = self._connection.execute(query, (chat_name, is_private))
        chat_id = cursor.lastrowid

        # Inserting the participants does not need to happen in the same
        # transaction as inserting the chat.
        participants = [(chat_id, user_id) for user_id in user_ids]
        query = 'INSERT INTO Participants (chat_id, user_id) VALUES (?, ?)'
        with self._connection:
            self._connection.executemany(query, participants)

        return Chat(chat_id, chat_name)

    def get_messages(self, chat_id):
        """Returns all messages for the chat with given chat_id."""
        query = 'SELECT * FROM Messages WHERE chat_id = ? ORDER BY message_ts'
        with self._connection:
            cursor = self._connection.execute(query, (chat_id,))
        return [Message(*row) for row in cursor.fetchall()]

    # TODO(eugenhotaj): Should we take in a Message instance here and check that
    # message_id == None? We then return a new Message with message_id = 
    # cursor.lastrowid.
    def insert_message(self, chat_id, user_id, message_text, message_ts):
        """Inserts a new message."""
        query = """INSERT INTO 
            Messages (chat_id, user_id, message_text, message_ts) 
            VALUES (?, ?, ?, ?)"""
        with self._connection:
            cursor = self._connection.execute(
                    query, (chat_id, user_id, message_text, message_ts))
        return Message(
                cursor.lastrowid, chat_id, user_id, message_text, message_ts)
