# -*- coding: utf-8 -*-

class BaseMiddleware(object):
    def __init__(self, callable_obj):
        self.callable = callable_obj
        self.request = callable_obj.request
        