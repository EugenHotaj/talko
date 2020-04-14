# Talko 🌮

*A fully functioning chat application built entierly from scratch (no HTTP, no 
frameworks)*.

At a high level, the application breaks down into a client-multiserver 
architecture. The client communicates with two servers via 
[JSON-RCP](https://www.jsonrpc.org/specification), a BroadcastServer and a 
DataServer. The DataServer handles reading and writing chat data from the 
database and operates in a traditional message protocol (i.e. request and 
response). The BroadcastServer handles fanning out new conversation messasges 
to all participants.

A primary goal of this project is to reinvent any wheel where it would be 
interesting to do so.
