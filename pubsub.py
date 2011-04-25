# -*- coding: utf-8 -*-

# Layer for implementation of Publisher/Subscription pattern in noodels
# This pattern is implemented via redis storage

import logging
import redis, json, gevent
try:
    from config import REDIS_HOST
except ImportError:
    REDIS_HOST = 'localhost'
from gevent.event import Event

class PubSubAgent(object):
    """
        Implement default Publisher/Subscriber agent. It has two functions - subscriber and
        publisher which are launched through greenlets.
        To use it override publisher function for depth handling connection,
        or just use this and specify pub_handler functions in instance
    """
    def __init__(self, channel, pub_handler = None, default_term = None):
        global REDIS_HOST
        self.channel = channel
        if pub_handler: self.pub_handler = pub_handler
        else: self.pub_handler = self.dumb

        self.default_term = default_term
        self.terminate_event = Event()
        
        # also create right here the publish redis connection
        self.pub_conn = redis.Redis()
        
    def dumb(self, msg):
        " Do nothing "
        return msg
        
    def publish(self, msg):
        "Publish msg to the agent channel"
        self.pub_conn.publish(self.channel, msg)
                
    def publisher(self):
        " This function listen opened ws socket, get JSON msg and publish it to self.chanel"
        while 1:
            try:
                msg = self.ws.receive()
            except Exception as e: # Some error occures, logg exception and terminate agent
                logging.error('Get exception %s' %  e.__repr__())
                self.ws.close()
                self.terminate_event.set() # send terminate_event event to subscriber
                return
            if msg: # Peer disconected
                msg = json.loads(msg)
                if self.default_term:
                    if msg[self.default_term]:
                        self.ws.close()
                        self.terminate_event.set() # send terminate_event event to subscriber
                msg = self.pub_handler(msg)
                #logging.debug('Sent msg %s' % msg.__repr__())
                self.publish(json.dumps(msg))
            else:
                self.ws.close()
                self.terminate_event.set()
                return
            if self.terminate_event.is_set():
                self.ws.close()
                return

    def subscriber(self):
        global REDIS_HOST
        rc_sub = redis.Redis(REDIS_HOST)
        rc_sub.subscribe([self.channel])
        listener = rc_sub.listen()
        while 1:
            msg = listener.next()
            if msg['type'] == 'message':
                try:
                    self.ws.send(msg['data'])
                except Exception as e: # Seems to be disconnected
                    logging.debug('Unsubscribe socket from channel no.%s ' % channel)
                    self.ws.close()
                    self.terminate_event.set()
                    return
            if self.terminate_event.is_set():
                self.ws.close()
                return

    def __call__(self, ws):
        self.ws = ws # web socket instance
        gevent.joinall([gevent.spawn(self.publisher), gevent.spawn(self.subscriber)])