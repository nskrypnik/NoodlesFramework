# -*- coding: utf-8 -*-

class BaseMiddleware(object):
    def __init__(self, callable):
        self.callable = callable
        self.request = callable.request
        