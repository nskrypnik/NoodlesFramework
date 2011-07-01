# -*- coding: utf-8 -*-

class BaseChannelHandler(object):
    """
        Base class for channel handlers. Abstract, use just for creation of other handler classes.
        Define functions for handling
    """
    handler_class = True
    
    def __init__(self, chid, session, data):
        if self.__class__.__name__ == 'BaseChannelHandler':
            raise NotImplemented('You shouldn\'t use this class directly')
        self.session = session
        self.chid = chid
        self.data = data
        self.op = data.get('op')
    
    def default(self):
        raise NotImplemented
    
    def response(self, data_to_send, chid = None):
        if not chid: chid = self.chid
        self.session.tosend(chid, data_to_send)
    
    def __getattr__(self):
        return None
    
    def __call__(self):
        if self.op:
            func = getattr(self, self.op)
            if func: func()
        else:
            self.default()
        
