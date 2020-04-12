"""Definition of the communication protocol between the clients and servers.

Two server types are supported:
    1. BroadcastServer
    2. DataServer

The BroadcastServer streams new conversation messages to connected users in 
real time. Users can only connect or disconnect to the server and listen for
new messages.

The DataServer reads and writes data into the database. It communicates with
clients via standard request/response based protocol.
"""

import dataclasses
from typing import List


def _parse_field(type_, value):
    return type_.from_json(value) if isinstance(value, dict) else value


class _Serializable:
    """A base class which implements JSON serialization for dataclasses."""

    def to_json(self):
        """Returns a JSON object representation of itself."""
        return dataclasses.asdict(self)

    @classmethod
    def from_json(cls, json):
        """Creates a new instance from the given JSON object."""
        kwargs = {}
        for field in dataclasses.fields(cls):
            type_, name, value = field.type, field.name, json[field.name]
            if isinstance(value, list):
                type_ = type_.__args__[0]
                kwargs[name] = [_parse_field(type_, v) for v in value]
            else:
                kwargs[name] = _parse_field(type_, value)
        return cls(**kwargs)
                    

# The classes below define the streaming conversation message protocol for the
# BroadcastServer.
@dataclasses.dataclass(frozen=True)
class OpenStreamRequest(_Serializable):
    user_id: int


@dataclasses.dataclass(frozen=True)
class OpenStreamResponse(_Serializable):
    pass


@dataclasses.dataclass(frozen=True)
class CloseStreamRequest(_Serializable):
    user_id: int


@dataclasses.dataclass(frozen=True)
class CloseStreamResponse(_Serializable):
    pass


@dataclasses.dataclass(frozen=True)
class BroadcastRequest(_Serializable):
    chat_id: int
    sender_id: int
    message_text: str
    receiver_ids: List[int]


@dataclasses.dataclass(frozen=True)
class BroadcastResponse(_Serializable):
    pass


# The classes below define the request/response protocol for the DataServer.
@dataclasses.dataclass(frozen=True)
class User(_Serializable):
    user_id: int
    user_name: str


@dataclasses.dataclass(frozen=True)
class Chat(_Serializable):
    chat_id: int
    chat_name: str


@dataclasses.dataclass(frozen=True)
class Message(_Serializable):
    message_id: int
    chat_id: int
    user_id: int
    message_text: str
    message_ts: int


@dataclasses.dataclass(frozen=True)
class InsertUserRequest(_Serializable):
    user_name: str


@dataclasses.dataclass(frozen=True)
class InsertUserResponse(_Serializable):
    user_id: int


@dataclasses.dataclass(frozen=True)
class GetChatsRequest(_Serializable):
    user_id: int


@dataclasses.dataclass(frozen=True)
class GetChatsResponse(_Serializable):
    chats: List[Chat]


@dataclasses.dataclass(frozen=True)
class InsertChatRequest(_Serializable):
    chat_name: str
    user_ids: List[int]


@dataclasses.dataclass(frozen=True)
class InsertChatResponse(_Serializable):
    chat_id: int


@dataclasses.dataclass(frozen=True)
class GetMessagesRequest(_Serializable):
    chat_id: int


@dataclasses.dataclass(frozen=True)
class GetMessagesResponse(_Serializable):
    messages: List[Message] 


@dataclasses.dataclass(frozen=True)
class InsertMessageRequest(_Serializable):
    chat_id: int
    user_id: int
    message_text: str


@dataclasses.dataclass(frozen=True)
class InsertMessageResponse(_Serializable):
    message_id: int
