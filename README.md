# Simple-WebSocket-Server

Simple WebSocket Server written in Python that supports multiple WebSocket connections. All messages sent to the server is in turn sent to the connected clients.

# Requirements:

- Python 3 as the API socketserver is used. If your Python version is lower than 3 an older version of socketserver must be used.
- The server is very simple, so only payload length < 126 is allowed.
- The only messages that can be sent are text messages and closing messages

# How Does It Work?

A socketserver is initialized and listens for client connections. When a client connects ThreadingMixIn starts a threaded handler for the connection. Every client connecting has to perform a handshake with the server to ensure that a proper WebSocket connection is made. After the handshake is completed the server and client can send masked messages to eachother until the connection is closed.

# Starting the Server:

Make sure `wss.py` and `server.py` are in the same folder.

Edit `server.py` to your preferences.

In the command line run `python server.py` and the server will start.

To shut down the server use `Ctrl+C`.

An example is provided in example_client.html and example_client.js. The example is based on a work assignment given at [websocket-example](https://github.com/ntnu-tdat2004/websocket-example)

# TODO:

- Log server activity to a file
- Cleanup of code

# References:
[socketserver examples](https://docs.python.org/3.4/library/socketserver.html/)

[socketserver source code](https://hg.python.org/cpython/file/3.4/Lib/socketserver.py/)

[RFC for WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
