-- Definition of the Users table.
CREATE TABLE Users
  (user_id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT NOT NULL);

-- TODO(eugenhotaj): Set up user1_id and user2_id as foreign keys.
-- TODO(eugenhotaj): Update database to allow group chats.
-- Definition of the private (i.e. one-on-one) Chats table and indicies.
CREATE TABLE Chats 
  (chat_id INTEGER PRIMARY KEY AUTOINCREMENT, 
   user1_id INTEGER NOT NULL,
   user2_id INTEGER NOT NULL);
CREATE INDEX ChatByUser1IdIndex ON Chats (user1_id);
CREATE INDEX ChatByUser2IdIndex ON Chats (user2_id);

-- TODO(eugenhotaj): Set up chat_id as a foreign key.
-- Definition of chat Messages table and index.
CREATE TABLE Messages 
  (message_id INTEGER PRIMARY KEY AUTOINCREMENT, 
   chat_id INTEGER NOT NULL,
   user_id INTEGER NOT NULL,
   message_text TEXT NOT NULL,
   message_ts INTEGER NOT NULL);
CREATE INDEX MessagesByChatIdIndex ON Messages (chat_id);
