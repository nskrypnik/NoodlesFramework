from gevent import monkey
monkey.patch_all()

# Gevent-socketio lib
from socketio import SocketIOServer
from noodles.http import Request, Response
from noodles.dispatcher import Dispatcher
from config import URL_RESOLVER, CONTROLLERS

#import zmqenv

resolver = __import__(URL_RESOLVER, globals(), locals())

# Create an dispatcher instance
dispatcher = Dispatcher(mapper=resolver.get_map(),
                        controllers = CONTROLLERS
                      )

# Our start point WSGI application
def noodlesapp(env, start_response):
    # Get request object
    request = Request(env, start_response)
    print "Try to handle url_path '%s'" % request.path
    # Get callable object with routine method to handle request
    callable_obj = dispatcher.get_callable(request)
    if not callable_obj:
        # May be here an error,raise exception
        raise Exception('Can\'t find callable for this url path')
    # Callable function must return Respone
    response = callable_obj()

    return response(env, start_response)

# Start server function, you may specify port number here
def startapp():
    try:
        from config import PORT
    except ImportError:
        PORT = 8088 # By defaultl 8088 debug port
    print 'Start server on %i...' % PORT
    SocketIOServer(('', PORT), noodlesapp, resource='socket.io').serve_forever()
