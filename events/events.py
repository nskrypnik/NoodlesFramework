# -*- coding: utf-8 -*-
"""
Created on Jul 29, 2011
filedesc: Small internal server events framework based on Redis
@author: Niko Skrypnik
"""


from noodles.redisconn import RedisConn
import gevent
import redis
import json
import logging


NOODLES_EVENTS_CHANNEL = '__noodles_events_channel'
NOODLES_EVENTS_LIST = {}

class NoodlesEventError(Exception):
    pass

class Event(object):
    "I'm event object"

    _events_id_key = ['__noodles_events_index']

    # Hack for saving memory
    @property
    def events_id_key(self):
        return self._events_id_key[0]

    def __init__(self):
        self.id = RedisConn.incr(self.events_id_key)
        self.callback = None

    def register(self, callback):
        "Register event in system "
        NOODLES_EVENTS_LIST[self.id] = self
        self.callback = callback

    def firing(self, event_data={}):
        event_msg = {'event_id': self.id, 'event_data': event_data}
        RedisConn.publish(NOODLES_EVENTS_CHANNEL, event_msg)
        print 'Event is firing'

    def unregister(self):
        NOODLES_EVENTS_LIST.pop(self.id)

def event_listener():
    print "event_listener:: i'm event listener"
    rc = redis.Redis()
    sub = rc.pubsub()
    sub.subscribe(NOODLES_EVENTS_CHANNEL)
    for msg in sub.listen():
        print "Some message: %s" % msg.__repr__()
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            event_id = data['event_id']
            event_data = data['event_data']
            event = NOODLES_EVENTS_LIST.get(event_id)
            if event:
                if not event_data:
                    event.callback()
                else: event.callback(event_data)
            else:
                logging.warning('Noodles events engine: Event#%i is unregistered' % event_id)

gevent.spawn(event_listener)
