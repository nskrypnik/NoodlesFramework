"""
Base handler class is defined from which a web socket channel
implementation is derived
"""
import json
import logging
import sys
from config import WS_CHANNELS, DEBUG, APICONTROLLERS

import redis
from gevent.event import Event
from noodles.geventwebsocket.handler import WebSocketHandler
from noodles.utils import datahandler
from noodles.utils.mailer import MailMan

from wssession import WSSession


try:
    from config import ENCODING
except ImportError:
    ENCODING = 'utf-8'


class WebSocketSendError(Exception):
    pass


class WebSocketError(Exception):
    pass


class MultiChannelWSError(Exception):
    pass


class WebSocketMessage(object):
    def __init__(self, data):
        if type(data) == dict:
            self.data = data
            return
        self.raw_data = data.encode(ENCODING)
        try:
            self.data = json.loads(self.raw_data)
        except:
            self.data = self.raw_data

    def __getattr__(self, name):
        if name == 'raw_data':
            self.raw_data = self.data
            return self.raw_data


class MultiSocketHandler(WebSocketHandler):
    """
    Abstract class for implementing server side web socket logic.

    Usage:
    1) Inherit your handler from WebSocketHandler class and override
        onopen, onmessage, onclose functions in controllers module

        class MyHandler(WebSocketHandler):

            def onopen(self):
                #some onopen logic

            def onmessage(self):
                #some onmessage logic

            def onclose(self):
                #some onclose logic

    2) Then urlmap this class in urls module
        urlmap(map, [
            ...
            ('/wsurl', 'controllers.MyHandler'),
            ...
        ])
    That's all!
    """

    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])
        self.close_event = Event()
        rc = redis.Redis()
        self.sub = rc.pubsub()
        self.controllers = {}
        for controller in APICONTROLLERS:
            # Import all controllers
            base_mod = __import__(controller, globals(), locals(), [], -1)
            mod = sys.modules.get(controller)
            if not mod:
                mod = base_mod
            self.controllers[controller] = mod

    def __call__(self, env, start_response):
        ws = env.get('wsgi.websocket')
        if not ws:
            raise WebSocketError('No server socket instance!')
        self.websocket = ws
        self.run_callback('open')
        # Endless event loop
        while 1:
            try:
                data = self.websocket.receive()
            except Exception as e:
                f = logging.Formatter()
                traceback = f.formatException(sys.exc_info())
                logging.error('Servlet fault: \n%s' % traceback)
                break
            # this is a stub to make dynamic channel open/close stuff
            # be ignored for now.
            if data:
                jd = json.loads(data)
                if jd['chid'] and jd['pkg'] == 'open':
                    logging.info('IGNORING DYNAMIC OPEN COMMAND %s' % data)
                    continue
                self.run_callback('message', WebSocketMessage(data))

            else:
                logging.debug('Web Socket is disconnected')
                self.close_event.set()
            if self.close_event.is_set():
                break
        self.run_callback('close')

    def run_callback(self, obj, args=None):

        try:
            assert hasattr(self, 'on%s' % obj)
            f = getattr(self, 'on%s' % obj)
            if args:
                return f(args)
            else:
                return f()
        except Exception as e:
            rt = self.onerror(json.dumps(str(e), separators=(', ', ':')))
            self.close()
            return rt

    def onopen(self):
        pass

    def onclose(self):
        pass

    def onmessage(self, msg):
        if type(msg.data) != dict:
            raise TypeError("""
                            Request object type is %s not dict!
                            """ % type(msg.data))
        action = msg.data.get('Action', False)
        if not action:
            raise ValueError("Action not found in request")
        route_res = self.mapper.match(action)
        controller = self.controllers.get(route_res.get('controller', False))
        if not controller:
            raise ValueError("Controller not found")
        handler = getattr(controller, route_res.get('action'))
        response = handler(msg.data.get('params', None))
        self.send(response)

    def onerror(self, e):
        """
        Send here Exception and traceback by Error channel
        """
        f = logging.Formatter()
        traceback = f.formatException(sys.exc_info())
        if DEBUG:
            err_message = {'chid': WS_CHANNELS['ERROR_CHID'],
                       'pkg': {'exception': e.__repr__(), 'tb': traceback}}
        else:
            err_message = {'chid': WS_CHANNELS['ERROR_CHID'],
                       'pkg': {'exception': 'error 500',
                               'tb': 'an error occured'}}
            MailMan.mail_send(MailMan(), e.__repr__(), traceback)
        self.websocket.send(json.dumps(err_message, separators=(', ', ':')))
        print traceback

    def dispatcher_routine(self):
        """
        This listens dispatcher redis channel and send data through channel
        """
        logging.info('subscribing to %s' % self.subscribe_name)
        self.sub.subscribe(self.subscribe_name)
        for msg in self.sub.listen():
            logging.info('CHANNEL %s < DISPATCHER MESSAGE %s' % (self, msg))
            self.websocket.send(json.loads(msg['data']))


class MultiChannelWS(MultiSocketHandler):
    """
    Use this class to implement virtual channels over web socket.
    To use it, inherit class from this and override init_channel function,
    where you can register all channel handlers by register_channel function

    Example:
    class MyWebSocket(MultiChannelWS):
        def init_channels(self):
            self.register_channel(0, NullChannelHandler)
            self.register_channel(1, FirstChannelHandler)
            ...
    """

    class ChannelSender(object):
        """
        Send channel message over websocket
        """
        def __init__(self, chid, _wsh):
            self.chid = chid
            self._wsh = _wsh

        def __call__(self, data):
            if type(data) != dict:
                raise TypeError("data is %s not dict" % type(data))
            package_to_send = {'chid': self.chid,
                               'pkg': data,
                               'session_params': self._wsh.session.params,
                               }
            data = json.dumps(package_to_send, default=datahandler)
            try:
                self._wsh.websocket.send(data)
            except:
                logging.warning('Can\'t send data to websocket!')

    def __init__(self, **kwargs):
        super(MultiChannelWS, self).__init__(**kwargs)
        self.channel_handlers = {}
        self.session = WSSession()

    def init_channels(self):
        "Override it to add new channel handlers by register_channel method"
        raise NotImplementedError('You must specify this function')

    def register_channel(self, chid, channel_handler_class):
        """
        Registers new channel with channel id - chid and channel handler
        class - channel_handler_class"""
        channel_handler = channel_handler_class(request=self.request)
        channel_handler.send = self.ChannelSender(chid, self)
        channel_handler.session = self.session
        self.channel_handlers[chid] = channel_handler

    def onopen(self):
        self.init_channels()
        for channel_handler in self.channel_handlers.values():
            channel_handler.onopen()

    def onclose(self):
        for channel_handler in self.channel_handlers.values():
            channel_handler.onclose()

    def onmessage(self, msg):
        chid = msg.data.get('chid')
        if chid == None:
            raise MultiChannelWSError('No such channel ID in request')
        channel_handler = self.channel_handlers.get(chid)
        if not channel_handler:
            raise MultiChannelWSError('No such channel')
        channel_handler.onmessage(WebSocketMessage(msg.data['pkg']))
