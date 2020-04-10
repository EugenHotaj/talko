# Notes
This is a living file which details design notes and idea.

## Message Based Communication (via HTTP/1.1?)
The client and server communicate via a custom JSON protocol over TCP socket 
streams. While this is needed to handle real time conversations, we also have
a need for message based communication, such as getting all participatns in a 
conversation.

We have two options to support message based communication which we discuss
below. We go with the first option for now as it is the most straightforward to
implement.

### Extending the protocol
The easiest option is to extend the JSON protocol to handle different types of 
requests. For example, to read/write data, the client can send `DataRequest`s
to the server. On the other hand, to broadcast conversation messages to users,
the client can send `BroadcastRequest`s. The server can similarly respond with
`DataResponse` or `BroadcastResponse` to deliver either data or conversation
messages to the client.

This approach is very straightforward. However, we're mixing together streaming
and messaging into the same protocol which is messy and unlikely to scale
(this is fine since Grima is not meant to be a production application). A 
further downside is that we're reinventing the wheel by creating this custom
protocol instead of using HTTP (this is also fine since the point of Grima is to
reinvent the wheel where it would be interesting to do so).

### HTTP/1.1
The second option is to update our server to understand HTTP/1.1 requests. The 
client can then request data from the server in the 'normal' fashion and use
the streaming protocol only when it wants to broadcast conversation messages. A
further benefit of this approach is that it more naturally allows us to factor 
out the data requests from the message broadcasting into different services 
(although we can do this with the above approach as well).


## Better Server Processes
The server uses a separate process for each client. Ultimately, processes 
should be decoupled from clients so the server can scale to handle many more
clients. One option for this is to have a client queue which is shared across
processes. Each client is put on the queue and worker processes take clients
off the queue, process them, and place them at the end of the queue. 

Of course, there are a number of issues with this approach: 
  1. The queue could become a bottleneck if there is a lot of contention from
     many processes reading and writing at the same time. 
  1. Clients could become starved if all processes are busy handling big 
     requests. We could maybe mitigate this with some kind of async 
     programming.
  1. Since we're using processes for "multithreading", context switching 
     between clients all the time could have high overhead. (It may also make
     sense to switch to threads entierly -- the code is highly I/O bound so we
     won't suffer too much penalty from the GIL).

A related approach is to have multiple client queues and assign subsets of 
processes to each queue. While this can mitigate issues 1, issues 2 and 3 would
still pose problems.


## Database Schema 
All the data is stored on-disk in a SQLite database. The schema is defined in 
the `schema.py` file.

At a high level, we store conversations in three tables, `Chats`, 
`Participants`, and `Messages`. Decoupling participants into a separate table
from conversations allows us to easily handle both private (one-on-one) and 
group conversations.

