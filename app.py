# -*- coding: utf-8 -*-
from gevent import monkey
from gevent.wsgi import WSGIServer
monkey.patch_all()

# Gevent-socketio lib
from websocket import server

from noodles.http import Request, Response
from noodles.dispatcher import Dispatcher
from noodles.session import SessionMiddleware 
from config import URL_RESOLVER, CONTROLLERS
import rediswrap
import logging

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

#import zmqenv

resolver = __import__(URL_RESOLVER, globals(), locals())

# Create an dispatcher instance
dispatcher = Dispatcher(mapper=resolver.get_map(),
                        controllers = CONTROLLERS
                      )

# Our start point WSGI application
def noodlesapp(env, start_response):
    # Get request object
    request = Request(env)
    #print "Try to handle url_path '%s'" % request.path
    # Get callable object with routine method to handle request
    callable_obj = dispatcher.get_callable(request)
    if not callable_obj:
        # May be here an error,raise exception
        raise Exception('Can\'t find callable for this url path')
    # Callable function must return Respone
    callable_obj = SessionMiddleware(callable_obj)
    response = callable_obj()

    return response(env, start_response)

# Start server function, you may specify port number here
def startapp():
    try:
        from config import PORT
    except ImportError:
        PORT = 8088 # By defaultl 8088 debug port
    print 'Start server on %i...' % PORT
    server.WebSocketServer(('', PORT), noodlesapp).serve_forever()
    #WSGIServer(('', PORT), noodlesapp).serve_forever()
