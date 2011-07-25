# -*- coding: utf-8 -*-
from websockhandler import WebSocketHandler

class WebSocket(object):
    """
        Object for Web Socket handling.
        Get an function f parameter. f is function that get an
        server socket instance ws and handle data from it
    """
    def __init__(self, f, *args, **kwargs):
        self.handler = f
        self.args = args
        self.kwargs = kwargs
    
    def __call__(self, env, start_response):
        start_response('200 OK',[('Content-Type','application/json')])
        #print env
        get_websocket = env.get('wsgi.get_websocket')
        ws = get_websocket()
        ws.do_handshake()
        # TODO: create Error object
        if not ws: raise Exception('No server socket instance!')
        self.handler(ws, *self.args, **self.kwargs)

def websocket(func):
    "Websocket decorator - launch function to handle websocket connection"
    def gen(request, *args, **kwargs):
        return WebSocket(func, *args, **kwargs)
    return gen
