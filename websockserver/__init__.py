"""WebSocket protocol implementation."""
import re
import struct
from random import randint, sample, choice
from hashlib import md5
from socket import error
from urlparse import urlsplit

from gevent.socket import create_connection
from gevent.coros import Semaphore

version_info = (0, 3, 0)
__version__ = '0.3dev'

# This class implements the WebSocket protocol draft version as of May 23, 2010
# The version as of August 6, 2010 will be implementend once Firefox or
# Webkit-trunk support this version.

# Connection is based on http://tools.ietf.org/html/draft-ietf-hybi-thewebsocketprotocol-03 (October 17, 2010)
# non-digits and non-spaces as required by the spec
# calculated as ''.join(map(chr, range(0x21, 0x2f) + range(0x3a, 0x7e)))
NONDIGITS = '''!"#$%&\'()*+,-.:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}'''
ALL = ''.join(map(chr, xrange(0, 255)))


class WebSocketError(error):
    pass


class BadRequest(WebSocketError):
    """This error will be raised by meth:`do_handshake` when encountering an invalid request.

    If left unhandled, it will cause :class:`WebSocketHandler` to log the error and to issue 400 reply.

    It will also be raised by :meth:`connect` if remote server has replied with 4xx error.
    """


class WebSocket(object):

    REQUEST = '''GET %s HTTP/1.1
Upgrade: WebSocket
Connection: Upgrade
Host: %s
Sec-WebSocket-Draft: 2
'''.replace('\n', '\r\n')

    def __init__(self, location, origin=None, protocol=None, key1=None, key2=None, socket=None, rfile=None, handler=None, secure=None):
        self.location = location
        self.origin = origin
        self.protocol = protocol
        self.key1 = key1
        self.key2 = key2
        self.socket = socket
        if rfile is None and socket is not None:
            rfile = socket.makefile()
        self.rfile = rfile
        self.handler = handler
        if secure is None:
            if location.startswith('ws://'):
                self.secure = False
            elif location.startswith('wss://'):
                self.secure = True
            else:
                raise ValueError('Location must start with "ws://" or "wss://": %r' % location)
        else:
            self.secure = secure
        self.handshaked = False
        self._writelock = Semaphore(1)

    def __repr__(self):
        try:
            info = ' ' + self.socket._formatinfo()
        except Exception:
            info = ''
        return '<%s at %s%s>' % (type(self).__name__, hex(id(self)), info)

    def do_handshake(self):
        """This method must be called before any send() or receive()

        Note: server-side only.
        """
        assert not self.handshaked, 'Already did handshake'
        if self.key1 is not None:
            # version 76
            if not self.key1:
                raise BadRequest("SEC-WEBSOCKET-KEY1 header is missing")
            if not self.key2:
                raise BadRequest("SEC-WEBSOCKET-KEY2 header is missing")
            part1 = self._get_key_value(self.key1)
            part2 = self._get_key_value(self.key2)
            headers = [
                ("Upgrade", "WebSocket"),
                ("Connection", "Upgrade"),
                ("Sec-WebSocket-Location", self.location),
            ]
            if self.origin is not None:
                headers.append(("Sec-WebSocket-Origin", self.origin))
            if self.protocol is not None:
                headers.append(("Sec-WebSocket-Protocol", self.protocol))
            self._send_reply("101 Web Socket Protocol Handshake", headers)

            # This request should have 8 bytes of data in the body
            key3 = self.rfile.read(8)
            challenge = md5(struct.pack("!II", part1, part2) + key3).digest()
            self.socket.sendall(challenge)
        else:
            # version 75
            headers = [
                ("Upgrade", "WebSocket"),
                ("Connection", "Upgrade"),
                ("WebSocket-Location", self.location),
            ]
            if self.origin is not None:
                headers.append(("WebSocket-Origin", self.origin))
            if self.protocol is not None:
                headers.append(("WebSocket-Protocol", self.protocol))
            self._send_reply("101 Web Socket Protocol Handshake", headers)
        self.handshaked = True

    def _send_reply(self, status, headers, message=None):
        assert not self.handler.response_length, '%s bytes already written' % self.handler.response_length
        towrite = ['HTTP/1.1 %s\r\n' % status]
        for header in headers:
            towrite.append("%s: %s\r\n" % header)
        towrite.append("\r\n")
        if message:
            towrite.append(message)
        msg = ''.join(towrite)
        self.socket.sendall(msg)
        self.handler.start_response(status, [])
        self.handler.response_length += len(msg)
        # we no longer need 'handler' so let's break the ref cycle early
        self.handler = None

    def _get_key_value(self, key_value):
        try:
            key_number = int(re.sub("\\D", "", key_value))
        except ValueError:
            raise BadRequest('Invalid key: %r' % (key_value,))
        spaces = re.subn(" ", "", key_value)[1]

        if key_number % spaces != 0:
            raise BadRequest("Key %r is not a multiple of spaces %r" % (key_value, spaces))

        return key_number / spaces

    def send(self, message):
        """Wrap a message into websocket framing and send.

        This method is safe to use from multiple greenlets.
        """
        assert self.handshaked, 'Call do_handshake() before calling send()'
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        with self._writelock:
            self.socket.sendall("\x00" + message + "\xFF")

    def detach(self):
        self.socket = None
        self.rfile = None
        self.handler = None

    def close(self):
        # XXX implement graceful close with 0xFF frame
        if self.socket is not None:
            try:
                self.socket.close()
            except Exception:
                pass
            self.detach()

    def _message_length(self):
        # TODO: buildin security agains lengths greater than 2**31 or 2**32
        length = 0

        while True:
            byte_str = self.rfile.read(1)

            if not byte_str:
                return 0
            else:
                byte = ord(byte_str)

            if byte != 0x00:
                length = length * 128 + (byte & 0x7f)
                if (byte & 0x80) != 0x80:
                    break

        return length

    def _read_until(self):
        bytes = []

        while True:
            byte = self.rfile.read(1)
            if ord(byte) != 0xff:
                bytes.append(byte)
            else:
                break

        return ''.join(bytes)

    def receive(self):
        assert self.handshaked, 'Call do_handshake() before calling receive()'
        while self.socket is not None:
            frame_str = self.rfile.read(1)
            if not frame_str:
                self.close()
                break
            else:
                frame_type = ord(frame_str)

            if not (frame_type & 0x80):  # most significant byte is not set
                if frame_type == 0x00:
                    bytes = self._read_until()
                    return bytes.decode("utf-8")
                else:
                    self.close()
            else:  # most significant byte is set
                # Read binary data (forward-compatibility)
                if frame_type != 0xff:
                    self.close()
                    break
                else:
                    length = self._message_length()
                    if length == 0:
                        self.close()
                        break
                    else:
                        self.rfile.read(length)  # discard the bytes

    def connect(self):
        parsed = urlsplit(self.location)
        if parsed.port is None:
            port = 443 if self.secure else 80
        else:
            port = parsed.port
        if parsed.port is not None:
            port = parsed.port
        hostport = parsed.hostname.lower()
        if (not self.secure and port != 80) or (self.secure and port != 443):
            hostport += ':%s' % port
        self._socket_connect((parsed.hostname, port))

        self.number1, self.key1 = self.generate_key()
        self.number2, self.key2 = self.generate_key()
        self.key3 = ''.join(sample(ALL, 8))

        self._send_initial_request(parsed.path, hostport)

        if self.rfile is None:
            self.rfile = self.socket.makefile()

        self._read_initial_response()
        self.handshaked = True

    def _socket_connect(self, address):
        if self.secure:
            from gevent.ssl import wrap_socket
        self.socket = create_connection(address)
        if self.secure:
            self.socket = wrap_socket(self.socket)

    def _send_initial_request(self, path, hostport):
        request = self.REQUEST % (path or '/', hostport)

        fields = []

        if self.origin is not None:
            fields.append('Origin: ' + self.origin + '\r\n')

        fields.append('Sec-WebSocket-Key1: %s\r\n' % self.key1)
        fields.append('Sec-WebSocket-Key2: %s\r\n\r\n' % self.key2)
        request += ''.join(fields)
        self.socket.sendall(request)

    def _read_initial_response(self):
        line = self.rfile.readline()
        if not line:
            raise WebSocketError('Server unexpectedly closed the connection')
        if not line.endswith('\r\n'):
            raise WebSocketError('Invalid response from server: %r' % (line,))

        if line[:8] == 'HTTP/1.1':
            line = line[8:].strip()
        else:
            raise WebSocketError('Invalid response from server: %r' % (line,))

        code = line.split(' ', 1)[0]
        if code != '101':
            if code.startswith('4'):
                raise BadRequest(line.strip())
            else:
                raise WebSocketError(line.strip())

        self.socket.sendall(self.key3)

        while True:
            line = self.rfile.readline()
            if not line.endswith('\r\n'):
                raise WebSocketError('Invalid response from server: %r' % (line,))
            line = line.strip()
            if not line:
                break
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            if key == 'upgrade':
                if value.lower() != 'websocket':
                    raise WebSocketError('Invalid value for "upgrade" in response: %r' % line)
            elif key == 'connection':
                if value.lower() != 'upgrade':
                    raise WebSocketError('Invalid value for "connection" in response: %r' % line)
            elif key in ('sec-websocket-origin', 'websocket-origin'):
                self.remote_origin = value
            elif key in ('sec-websocket-protocol', 'websocket-protocol'):
                self.remote_protocol = value

        expected = md5(self.number1 + self.number2 + self.key3).digest()
        challenge = self.rfile.read(16)
        if challenge != expected:
            raise WebSocketError('Challenge mismatch: expected %r, got %r' % (expected, challenge))

    def generate_key(self):
        spaces = randint(1, 12)
        maxim = 4294967295 / spaces
        number = randint(0, maxim)
        product = number * spaces
        key = str(product)
        key = choice(NONDIGITS) + key
        # XXX actually required to insert 1-12 NONDIGITS at random places
        return struct.pack('>I', number), key[:1] + (' ' * spaces) + key[1:]
        # XXX actually required to insert spaces at random places

    def getsockname(self):
        return self.socket.getsockname()

    def getpeername(self):
        return self.socket.getpeername()
