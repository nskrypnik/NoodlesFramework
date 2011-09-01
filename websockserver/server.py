'''
filedesc: base websocket implementation on top of gevent
'''
import sys
import traceback
from socket import error, SHUT_WR
from datetime import datetime
from gevent.pywsgi import WSGIHandler, WSGIServer

from noodles.websockserver.policyserver import FlashPolicyServer
from noodles.websockserver import WebSocket, BadRequest

import gevent
assert gevent.version_info >= (0, 13, 2), 'Newer version of gevent is required to run websocket.server'

__all__ = ['WebSocketHandler', 'WebSocketServer']


class WebSocketHandler(WSGIHandler):

    WebSocket = WebSocket
    websocket = None

    def is_websocket(self):
        if 'upgrade' not in self.environ.get('HTTP_CONNECTION', '').lower():
            return False
        if self.environ.get('HTTP_UPGRADE', '').lower() != "websocket":
            return False
        return True

    def get_websocket(self, environ=None):
        if self.websocket is not None:
            return self.websocket
        if environ is None:
            environ = self.environ
        origin = environ.get('HTTP_ORIGIN')
        protocol = environ.get('HTTP_SEC_WEBSOCKET_PROTOCOL')
        if environ['wsgi.url_scheme'] == 'https':
            location = 'wss://' + environ['HTTP_HOST'] + environ['PATH_INFO']
        else:
            location = 'ws://' + environ['HTTP_HOST'] + environ['PATH_INFO']
        key1 = environ.get('HTTP_SEC_WEBSOCKET_KEY1')
        key2 = environ.get('HTTP_SEC_WEBSOCKET_KEY2')
        self.websocket = self.WebSocket(location, origin, protocol, key1, key2, self.socket, self.rfile, self)
        return self.websocket

    def run_application(self):
        if self.is_websocket():
            self.environ['wsgi.get_websocket'] = self.get_websocket
            try:
                self.result = self.application(self.environ, self.start_response)
                if self.result is not None:
                    self.process_result()
            except BadRequest, ex:
                ex = str(ex) or 'Bad Request'
                self.log_error(ex)
                if self.websocket is not None and self.websocket.handshaked:
                    self.websocket.close()
                elif not self.response_length:
                    self.start_response('400 Bad Request', [('Connection', 'close')])
                    self.write('')
                if self.websocket is not None:
                    self.websocket.detach()
                    self.websocket = None
            except:
                if self.websocket is not None:
                    self.websocket.close()
                raise
            finally:
                if self.websocket is not None:
                    self.socket = None
                    self.websocket = None
                self.environ.pop('wsgi.get_websocket', None)
        else:
            return WSGIHandler.run_application(self)

    def read_requestline(self):
        data = self.rfile.read(7)
        if data[:1] == '<':
            try:
                data += self.rfile.read(15)
                if data.lower() == '<policy-file-request/>':
                    self.socket.sendall(self.server.flash_policy)
                else:
                    self.log_error('Invalid request: %r', data)
            finally:
                self.socket.shutdown(SHUT_WR)
                self.socket.close()
                self.socket = None
        else:
            return data + self.rfile.readline()


class WebSocketServer(WSGIServer):

    handler_class = WebSocketHandler

    def __init__(self, listener, application=None, policy_server=True, flash_policy=True, backlog=None,
                 spawn='default', log='default', handler_class=None, environ=None, **ssl_args):
        if flash_policy is True:
            self.flash_policy = FlashPolicyServer.policy
        else:
            self.flash_policy = flash_policy
        if policy_server is True:
            self.policy_server = FlashPolicyServer(policy=self.flash_policy)
        elif hasattr(policy_server, 'start'):
            self.policy_server = policy_server
        elif policy_server:
            self.policy_server = FlashPolicyServer(policy_server, policy=self.flash_policy)
        else:
            self.policy_server = None
        super(WebSocketServer, self).__init__(listener, application, backlog=backlog, spawn=spawn, log=log,
                                              handler_class=handler_class, environ=environ, **ssl_args)

    def start_accepting(self):
        self._start_policy_server()
        super(WebSocketServer, self).start_accepting()
        self.log_message('%s accepting connections on %s', self.__class__.__name__, _format_address(self))

    def _start_policy_server(self):
        server = self.policy_server
        if server is not None:
            try:
                server.start()
                self.log_message('%s accepting connections on %s', server.__class__.__name__, _format_address(server))
            except error, ex:
                sys.stderr.write('FAILED to start %s on %s: %s\n' % (server.__class__.__name__, _format_address(server), ex))
            except Exception:
                traceback.print_exc()
                sys.stderr.write('FAILED to start %s on %s\n' % (server.__class__.__name__, _format_address(server)))

    def kill(self):
        if self.policy_server is not None:
            self.policy_server.kill()
        super(WebSocketServer, self).kill()

    def log_message(self, message, *args):
        log = self.log
        if log is not None:
            try:
                message = message % args
            except Exception:
                traceback.print_exc()
                try:
                    message = '%r %r' % (message, args)
                except Exception:
                    traceback.print_exc()
#            log.write('%s %s\n' % (datetime.now().replace(microsecond=0), message))


def _format_address(server):
    try:
        if server.server_host == '0.0.0.0':
            return ':%s' % server.server_port
        return '%s:%s' % (server.server_host, server.server_port)
    except Exception:
        traceback.print_exc()
