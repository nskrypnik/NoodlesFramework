# -*- coding: utf-8 -*-

from gevent.event import Event

import logging
import sys

try:
    from config import ENCODING
except ImportError:
    ENCODING = 'utf-8'

class WebSocketSendError(Exception):
    pass

class WebSocketError(Exception):
    pass

class WebSocketMessage(object):
    
    def __init__(self, data):
        self.raw_data = data.encode(ENCODING)
        try:
            self.data = json.loads(self.raw_data)
        except:
            self.data = self.raw_data


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
    
    def __new__(cls, request):
        _inst = object.__new__(cls, request)
        return _inst
    
    def __init__(self, request):
        self.request = request
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
        raise NotImplementedError('onopen function must be implemented')
    
    def onclose(self):
        raise NotImplementedError('onclose function must be implemented')
    
    def onmessage(self, msg):
        raise NotImplementedError('onmessage function must be implemented')
    
    def onerror(self, e):
        raise NotImplementedError('onerror function must be implemented')
    
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