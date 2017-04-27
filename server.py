from wss import WebSocketServer

server = WebSocketServer(8080, 'localhost')
server.listen_forever()
