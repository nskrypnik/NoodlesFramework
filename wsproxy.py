# -*- coding: utf-8 -*-

import gevent
import logging
import sys
import traceback
import json

from noodles.http import websocket
from gevent.queue import Queue
from gevent.event import Event
from config import CHANNEL_HANDLERS_TABLE
try:
    from config import ECHO_CHID
except:
    ECHO_CHID = 101 # default Echo channel id
try:
    from config import ERROR_CHID
except:
    ERROR_CHID = 500 # default Echo channel id

def echo_channel_handler(chid, session, data):
    " Example channel handler - pass to it channel ID chid, session object, and data "
    session.tosend(chid, data) # just echo

# Update CHANNEL_HANDLERS_TABLE and add to it echo channel handler
CHANNEL_HANDLERS_TABLE.update({ECHO_CHID: echo_channel_handler})

class ErrorChannelID(Exception):
    pass
    
class WSSession(object):
    """
        Represent all information about web socket session, and provide
        interface to send data through web socket
    """
    
    def __init__(self):
        self.output_queue = Queue()
        self.params = {} # Session specific parameters
        self.greenlets = {} # The dictionary that storages all greenlets associated with this session
        # except of input/output servelet handlers and main servelet function
        self.terminators = {} # list of functions for execute while session is terminating
        
    def tosend(self, chid, data):
        " Provide ability to send data through websocket by chid "
        self.output_queue.put({'chid': chid, 'pkg': data, 'session_params': self.params})
   
    def del_greenlet(self, greenlet_name):
        g = self.greenlets[greenlet_name]
        gevent.kill(g)
    
    def add_greenlet(self, func, terminator = None):
        """ Add some greenlet with function func to session,
            terminator is function that executes after killing of greenlet
        """
        pass # while pass
    
    def kill_greenlets(self):
        " Kill all greenlets associated with this session "
        for green in self.greenlets.values():
            logging.debug('Kill greenlet for session')
            gevent.kill(green)
    
    def terminate(self):
        for t in self.terminators.values():
            t(self)
    
    def __getattr__(self, name):
        " If we try to access to some property isn't existed, returns None"
        return None
    
    def __setattr__(self, name, value):
        self.__dict__.update({name: value})    

class WSServelet(object):
    " Instance that serves web socket connection with client "
    channel_handlers = CHANNEL_HANDLERS_TABLE
    
    def __init__(self, ws):
        self.ws = ws
        self.terminate_event = Event()
        self.sess = WSSession() # create servelet session

    def serve(self, data):
        """
            This function serve request from client.
            It separates channels and calls channels handlers.
            Also updates Web Socket session parameters 
        """
        data = json.loads(data)
        chid = data.get('chid')
        if chid:
            #logging.debug('Channel id is %i' % chid)
            session_params = data.get('session_params')
            if session_params: self.sess.params.update(session_params)
            # get channel handler
            handler = self.channel_handlers.get(chid)
            if handler:
                if hasattr(handler, 'handler_class'):
                    handler(chid, self.sess, data['pkg'])() # call channel handler
                else:
                    handler(chid, self.sess, data['pkg']) # Launch oldstyle handler
            else:   
                raise ErrorChannelID('No such channel handler')
        else:
            raise ErrorChannelID('No channel id')

    def terminate(self):
        self.terminate_event.set()
    
    def output_handler(self):
        while 1:
            data = self.sess.output_queue.get()
            try:
                self.ws.send(json.dumps(data))
            except Exception as e:
                logging.error(e.__repr__())
                self.terminate()
                return
    
    def input_handler(self):
        while 1:
            try:
                data = self.ws.receive()
            except Exception as e:
                f = logging.Formatter()
                traceback = f.formatException(sys.exc_info())
                logging.error('Servelet fault: \n%s' % traceback)
                self.terminate()
                return 
            
            if data:
                try:
                    logging.debug('Receive %s' % data)
                    self.serve(data)
                except Exception as e:
                    # Send error message
                    f = logging.Formatter()
                    traceback = f.formatException(sys.exc_info())
                    logging.debug(traceback) # log traceback
                    err_message = {'chid': ERROR_CHID, 'pkg': {'exception': e.__repr__(), 'tb': traceback}}
                    self.ws.send(json.dumps(err_message))
            else: #data is None
                logging.debug('Web Socket is disconnected')
                self.terminate()
                return
        
    def __call__(self):
        i = gevent.spawn(self.input_handler)
        o = gevent.spawn(self.output_handler)
        self.terminate_event.wait()
        # Terminate servelet and all greenlets
        self.sess.kill_greenlets()
        gevent.kill(i); gevent.kill(o)
        self.sess.terminate()

@websocket
def run_servelet(ws):
    servelet = WSServelet(ws)
    servelet()
