# -*- coding: utf-8 -*-

from gevent.event import Event
from wssession import WSSession

import logging
import sys
import json

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
            self.raw_data = json.dumps(self.data)
            return self.raw_data
            
            


class WebSocketHandler(object):
    """
        Abstract class for implementing server side web socket logic.
        
        Using:
        
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
    
    def __call__(self, env, start_response):
        start_response('200 OK',[('Content-Type','application/json')])
        get_websocket = env.get('wsgi.get_websocket')
        ws = get_websocket()
        ws.do_handshake()
        if not ws: raise WebSocketError('No server socket instance!')
        self.ws = ws
        
        self.onopen()
        # Endless event loop
        while 1:
            try:
                data = self.ws.receive()
            except Exception as e:
                f = logging.Formatter()
                traceback = f.formatException(sys.exc_info())
                logging.error('Servelet fault: \n%s' % traceback)
                break
            
            if data:
                try:
                    self.onmessage(WebSocketMessage(data))
                except Exception as e:
                    self.onerror(e)
            else:
                logging.debug('Web Socket is disconnected')
                self.close_event.set()
            
            if self.close_event.is_set():
                break
        
        self.onclose()
                
    
    def onopen(self):
        pass
    
    def onclose(self):
        pass
    
    def onmessage(self, msg):
        pass
    
    def onerror(self, e):
        pass
    
    def send(self, data):
        if type(data) == dict:
            data = json.dumps(data)            
        else:
            if type(data) != str:
                raise WebSocketSendError('Sended value must be string or dictionary type')
        try:
            self.ws.send(data)
        except:
            # seems to be disconnected
            self.onclose()

class MultiChannelWS(WebSocketHandler):
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
        
        def __init__(self, chid, _wsh):
            self.chid = chid
            self._wsh = _wsh
            
        def __call__(self, data):
            package_to_send = {'chid': self.chid, 
                               'pkg': data,
                               'session_params': self._wsh.session.params,
                               }
            self._wsh.send(package_to_send)

    def __init__(self, **kwargs):
        super(MultiChannelWS, self).__init__(**kwargs)
        self.channel_handlers = {}
        self.session = WSSession()
            
    def init_channels(self):
        "Override it to add new channel handlers by register_channel method"
        raise NotImplementedError('You must specify this function')
    
    def register_channel(self, chid, channel_handler_class):
        "Registers new channel with channel id - chid and channel handler class - channel_handler_class"
        channel_handler = channel_handler_class(request = self.request)
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
        
        
        