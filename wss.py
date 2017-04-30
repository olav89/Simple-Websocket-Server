from base64 import b64encode
import hashlib
from socketserver import ThreadingMixIn, TCPServer, StreamRequestHandler

# https://hg.python.org/cpython/file/3.4/Lib/socketserver.py
# https://docs.python.org/3.4/library/socketserver.html

# https://tools.ietf.org/html/rfc6455
# Frames are sent as detailed below:
#0                   1                   2                   3
#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#+-+-+-+-+-------+-+-------------+-------------------------------+
#|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
#|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
#|N|V|V|V|       |S|             |   (if payload len==126/127)   |
#| |1|2|3|       |K|             |                               |
#+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
#|     Extended payload length continued, if payload len == 127  |
#+ - - - - - - - - - - - - - - - +-------------------------------+
#|                               |Masking-key, if MASK set to 1  |
#+-------------------------------+-------------------------------+
#| Masking-key (continued)       |          Payload Data         |
#+-------------------------------- - - - - - - - - - - - - - - - +
#:                     Payload Data continued ...                :
#+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
#|                     Payload Data continued ...                |
#+---------------------------------------------------------------+

# opcodes
OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA

# handler for client connections and their communication
class WebSocketHandler(StreamRequestHandler):
    def __init__(self, socket, address, server):
        self.server = server # to access servers top level functionality
        StreamRequestHandler.__init__(self, socket, address, server)

    def setup(self):
        StreamRequestHandler.setup(self)
        self.conn_keep_alive = True # decides if the connection should be kept alive
        self.handshake_success = False # WebSocket handshake
        self.read_key = "" # the key read from WebSocket handshake
        self.read_upgr_param = False # whether the WebSocket handshake contained the upgrade parameter

    def handle(self):
        while self.conn_keep_alive:
            if not self.handshake_success: # perform handshake if it has not been done successfully
                self.perform_handshake()
            else: # else receive frame
                self.receive_frame()

    def perform_handshake(self):
        data = self.rfile.readline().strip() # read header-lines
        if len(data) > 0: # reading header-lines
            if str(data).find("Upgrade: websocket") > -1: # found the upgrade parameter
                self.read_upgr_param = True
            if str(data).find("Sec-WebSocket-Key:") > -1: # found the key
                self.read_key = str(data)[21:-1]
        else: # last header-line is empty
            if not self.read_upgr_param: # upgrade parameter not found, close connection
                print('Upgrade parameter missing')
                self.conn_keep_alive = False;
                return
            elif len(self.read_key) < 1: # key not found, close connection
                print('Client missing key')
                self.conn_keep_alive = False;
                return
            else: # key and upgrade parameter found, compute the response header
                magic_key = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
                h = hashlib.sha1();
                h.update(self.read_key.encode())
                h.update(magic_key.encode())
                reply_key = b64encode(h.digest()).strip().decode('ASCII')
                reply = 'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n' % reply_key;
                self.handshake_success = self.wfile.write(reply.encode())
                self.server.new_client(self)

    def receive_frame(self):
        # support only payload len < 126!!!
        # the reading of a package is to read bytes as below:
        # 1 byte for fin-rsv123-opcode
        # 1 byte for mask and payload len
        # 4 bytes for masking-key
        # payload len bytes of payload data

        try:
            h1, h2 = self.rfile.read(2)
        except Exception as e: # error reading
            h1, h2 = 0, 0

        # FIN RSV1 RSV2 RSV3 OPCODE(4)
        # MASK LEN(7)
        fin = h1 & 0x80 # 0x80 = 1000 0000
        opcode = h1 & 0x0f # 0x0f = 0000 1111
        masked = h2 & 0x80 # 0x80 = 1000 0000
        message_len = h2 & 0x7f # 0x7f = 0111 1111

        if not h1: # could not read
            print('Connection was closed.')
            self.server.remove_client(self)
            self.conn_keep_alive = False
            return
        elif opcode == OPCODE_CLOSE: # client wants to close connection
            print('Closing connection to client %d.' % self.server.get_handlers_client(self)['id'])
            self.send_to_client('', OPCODE_CLOSE) # send confirmation back to client
            self.server.remove_client(self)
            self.conn_keep_alive = False
            return
        elif not masked: # payload is not masked
            print('Message was not masked.')
            return
        elif opcode == OPCODE_TEXT:
            if message_len > 125: # only short messages supported
                print('Message was too long.')
                return

            masking = self.rfile.read(4) # read the masks
            payload = self.rfile.read(message_len) # read the payload

            message = ""; # decoded message
            i = 0;
            for b in payload:
                b = b ^ masking[i%4]
                message += chr(b)
                i += 1
            print('Message received from client %d: %s.' % (self.server.get_handlers_client(self)['id'], message))
            self.server.message_all(message, OPCODE_TEXT) # send the message to all connected clients
            return
        elif opcode == OPCODE_BINARY or opcode == OPCODE_PING or opcode == OPCODE_PONG or OPCODE_CONTINUATION:
            print('No implementation for opcode: %d.' % opcode)
            return


    def send_to_client(self, message, opcode):
        header = bytearray()
        header.append(0x80 | OPCODE_TEXT) # FIN and opcode
        payload = message.encode('utf-8')
        payload_len = len(payload)
        if (payload_len < 126):
            header.append(payload_len)
        else:
            print('Payload is too large to deliver for message: %s.' % message)
            return
        self.wfile.write(header + payload)

# The server
class WebSocketServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True # can use same address
    daemon_threads = True # exit even when threads are running

    clients = [] # save all connected clients
    counter = 0 # counter used for client id

    def __init__(self, port, host):
        self.port = port
        TCPServer.__init__(self, (host, port), WebSocketHandler)

    def listen_forever(self):
        try:
            print('Listening for clients on port %d' % self.port)
            self.serve_forever()
        except KeyboardInterrupt: # Ctrl+C
            self.server_close()
            print('Server shutting down')
        except Exception as e: # Error occured
            self.server_close()
            print(str(e))

    def new_client(self, handler):
        self.counter += 1
        client = { # save id for prints and handler to send messages
            'id': self.counter,
            'handler': handler
        }
        self.clients.append(client)
        print('Client %d connected.' % self.counter)

    def remove_client(self, handler):
        for client in self.clients:
            if client['handler'] == handler:
                self.clients.remove(client)

    def get_handlers_client(self, handler):
        for client in self.clients:
            if client['handler'] == handler:
                return client

    def message_all(self, message, opcode):
        for client in self.clients:
            client['handler'].send_to_client(message, opcode)
