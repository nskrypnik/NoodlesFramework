# -*- coding: utf-8 -*-

class BaseChannelHandler(object):
    """
        Base class for channel handlers. Abstract, use just for creation of other handler classes.
        Define functions for handling
    """
    handler_class = True
    
    def __init__(self, chid, session):
        if self.__class__.__name__ == 'BaseChannelHandler':
            raise NotImplemented('You shouldn\'t use this class directly')
        self.session = session
        self.chid = chid
        #self.op = data.get('op')
    
    def default(self):
        raise NotImplemented
    
    def response(self, data_to_send, chid = None):
        if not chid: chid = self.chid
        self.session.tosend(chid, data_to_send)
    
    def __getattr__(self, name):
        return None
    
    def __call__(self, data = None):
        op = data.get('op')
        if op:
            func = getattr(self, op)
            if func: func(data)
            else:
                raise Exception('Unknown operation on channel')
        else:
            self.default(data)
        
    
