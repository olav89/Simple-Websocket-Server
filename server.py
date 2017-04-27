from wss import WebSocketServer

server = WebSocketServer(9001, 'localhost')
server.listen_forever()
