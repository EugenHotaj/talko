PRAGMA foreign_keys = ON;

CREATE TABLE Users
  (user_id INTEGER PRIMARY KEY AUTOINCREMENT, 
   user_name TEXT NOT NULL);

CREATE TABLE Chats 
  (chat_id INTEGER PRIMARY KEY AUTOINCREMENT, 
   chat_name TEXT NOT NULL);

CREATE TABLE Participants
  (participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
   chat_id INTEGER NOT NULL,
   user_id INTEGER NOT NULL,
   FOREIGN KEY(chat_id) REFERENCES Chats(chat_id),
   FOREIGN KEY(user_id) REFERENCES Users(user_id));
CREATE INDEX ParticipantsByChatId ON Participants(chat_id);
CREATE INDEX ParticipantsByUserId ON Participants(user_id);

CREATE TABLE Messages 
  (message_id INTEGER PRIMARY KEY AUTOINCREMENT, 
   chat_id INTEGER NOT NULL,
   user_id INTEGER NOT NULL,
   message_text TEXT NOT NULL,
   message_ts INTEGER NOT NULL,
   FOREIGN KEY(chat_id) REFERENCES Chats(chat_id),
   FOREIGN KEY(user_id) REFERENCES Users(user_id));
CREATE INDEX MessagesByChatIdIndex ON Messages (chat_id);
