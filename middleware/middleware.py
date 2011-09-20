# -*- coding: utf-8 -*-
'''
filedesc: framework middleware base class
'''
import sys

class MiddlewareLoadError(Exception):
    pass

class BaseMiddleware(object):
    def __init__(self, callable_obj):
        self.callable = callable_obj
        self.request = callable_obj.request

class AppMiddlewares(list):
    "Class represents application middlewares"

    def __init__(self, MIDDLEWARES):
        "Give MIDDLEWARES - raw list of middlewares and stores dict of classes itself"
        super(AppMiddlewares, self).__init__()
        MIDDLEWARES.reverse()
        for middleware_path in MIDDLEWARES:
            middleware_class_name = middleware_path.split('.')[-1]
            middleware_module = middleware_path.split('.')[:-1]
            middleware_module = '.'.join(middleware_module)
            base_mod = __import__(middleware_module, globals(), locals())
            mod = sys.modules.get(middleware_module)
            if not mod: mod = base_mod
            try:
                self.append(getattr(mod, middleware_class_name))
            except AttributeError:
                MiddlewareLoadError('No such class %s in %s module' % (middleware_class_name,
                                                                       middleware_module))
