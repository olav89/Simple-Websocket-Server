# Simple-WebSocket-Server

Simple WebSocket Server written in Python.

# Requirements:

- Python 3 as the API socketserver is used. If your Python version is lower than 3 an older version of socketserver must be used.
- The server is very simple, so only payload length < 126 is allowed.
- The only messages that can be sent are text messages and closing messages

# How Does It Work?

- A socketserver is initialized and listens for client connections.
- When a client connects ThreadingMixIn starts a threaded handler for the connection.
- Every client connecting has to perform a handshake with the server to ensure that a proper WebSocket connection is made.
- After the handshake is completed the server and client can send masked messages to eachother until the connection is closed.

# TODO:

- Log server activity to a file
- Cleanup of code 

# References:

https://hg.python.org/cpython/file/3.4/Lib/socketserver.py (Source code for socketserver)
https://docs.python.org/3.4/library/socketserver.html (Code examples for using socketserver)
https://tools.ietf.org/html/rfc6455 (The WebSocket Protocol)
