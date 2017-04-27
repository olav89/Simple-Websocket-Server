from base64 import b64encode
import hashlib
from socketserver import ThreadingMixIn, TCPServer, StreamRequestHandler

# https://hg.python.org/cpython/file/3.4/Lib/socketserver.py
# https://docs.python.org/3.4/library/socketserver.html

# https://tools.ietf.org/html/rfc6455
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

# headers
# support only payload len < 126!!!
# 8 bits for fin-opcode
# 8 bits for mask and payload len

# opcodes
opcode_continuation = 0x0
opcode_text = 0x1
opcode_binary = 0x2
opcode_close = 0x8
opcode_ping = 0x9
opcode_pong = 0xA


class WebSocketHandler(StreamRequestHandler):
    def __init__(self, socket, address, server):
        self.server = server
        StreamRequestHandler.__init__(self, socket, address, server)

    def setup(self):
        StreamRequestHandler.setup(self)
        self.connection_active = True
        self.handshake_success = False
        self.client_valid = False
        self.read_key = ""
        self.upgrade_param = False

    def handle(self):
        #print('Handle event')
        while self.connection_active:
            if not self.handshake_success:
                self.do_handshake()
            elif self.client_valid:
                self.get_message()

    def do_handshake(self):
        data = self.rfile.readline().strip()
        if len(data) > 0: # reading headers
            if str(data).find("Upgrade: websocket") > -1:
                self.upgrade_param = True
                #print('Found Upgrade')
            if str(data).find("Sec-WebSocket-Key:") > -1:
                self.read_key = str(data)[21:-1]
                #print('Found Key')
        else: # finished reading headers7
            #print(self.upgrade_param)
            #print(self.read_key)
            if not self.upgrade_param:
                print('Upgrade parameter missing')
                self.connection_active = False;
                return
            elif len(self.read_key) < 1:
                print('Client missing key')
                self.connection_active = False;
                return
            else:
                magic_key = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
                h = hashlib.sha1();
                h.update(self.read_key.encode())
                h.update(magic_key.encode())
                reply_key = b64encode(h.digest()).strip().decode('ASCII')
                reply = 'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n' % reply_key;
                self.client_valid = True
                self.handshake_success = self.wfile.write(reply.encode())
                self.server.new_client(self)

    def get_message(self):
        try:
            h1, h2 = self.rfile.read(2)
        except Exception as e: # connection is closed
            h1, h2 = 0, 0
        # FIN RSV1 RSV2 RSV3 OPCODE(4)
        # MASK LEN(7)
        fin = h1 & 0x80 # 0x80 = 1000 0000
        opcode = h1 & 0x0f # 0x0f = 0000 1111
        masked = h2 & 0x80 # 0x80 = 1000 0000
        message_len = h2 & 0x7f # 0x7f = 0111 1111

        if not h1:
            print('Connection was closed')
            self.server.remove_client(self)
            self.connection_active = False
            return
        elif opcode == opcode_close:
            print('Closing connection')
            self.server.remove_client(self)
            self.connection_active = False
            return
        elif not masked:
            print('Message was not masked')
            return
        elif opcode == opcode_text:
            if message_len > 125: # only short messages supported
                print('Message was too long')
                return

            masking = self.rfile.read(4) # read the masks
            payload = self.rfile.read(message_len) # read the payload

            message = "";
            i = 0;
            for b in payload:
                b = b ^ masking[i%4]
                message += chr(b)
                i += 1
            print('Message received from client %d: %s' % (self.server.get_handlers_client(self)['id'], message))
            self.server.message_all(message)
            return
        elif opcode == opcode_binary or opcode == opcode_ping or opcode == opcode_pong or opcode_continuation:
            print('No implementation for opcode: %d' % opcode)
            return


    def send_message(self, message):
        header = bytearray()
        header.append(0x80 | opcode_text) # FIN and opcode
        payload = message.encode('utf-8')
        payload_len = len(payload)
        if (payload_len < 126):
            header.append(payload_len)
        else:
            print('Payload is too large to deliver for message: %s' % message)
            return
        print("Sending payload: %s" % payload)
        self.wfile.write(header + payload)


class WebSocketServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads = True # exit even when threads are running

    clients = []
    counter = 0

    def __init__(self, port, host):
        self.port = port
        TCPServer.__init__(self, (host, port), WebSocketHandler)

    def listen_forever(self):
        try:
            print('Listening for clients on port %d' % self.port)
            self.serve_forever()
        except KeyboardInterrupt:
            self.server_close()
            print('Server shutting down')
        except Exception as e:
            self.server_close()
            print(str(e))
            exit(1)

    def new_client(self, handler):
        self.counter += 1
        client = {
            'id': self.counter,
            'handler': handler,
            'address': handler.client_address
        }
        self.clients.append(client)
        print('Client added: %s' % str(handler.client_address))

    def remove_client(self, handler):
        for client in self.clients:
            if client['handler'] == handler:
                self.clients.remove(client)

    def get_handlers_client(self, handler):
        for client in self.clients:
            if client['handler'] == handler:
                return client

    def message_all(self, message):
        for client in self.clients:
            client['handler'].send_message(message)
