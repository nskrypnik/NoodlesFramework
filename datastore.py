# -*- coding: utf-8 -*-
import re, logging

non_record = re.compile(r'__\w+__')

class Model(object):
    " General class for objects description in data storage "
    __structure__ = {}
    def __init__(self):
        # create dictionary for model instance
        self.__instdict__ = {}
        # Check static model structure
        if not self.__structure__:
        # if non - create it
            logging.debug('Creating structure for model %s' % self.__class__.__name__)
            # Browse model for properties
            for key in dir(self):
                if not non_record.match(key):
                    value = getattr(self, key)
                    if hasattr(value, '__isvalue__'):
                        value.set_key(key)
                        self.__structure__[key] = None
        self.__instdict__ = self.__structure__.copy()
        
    def __getattr__(self, attr):
        pass
                 

class Value(object):
    "Single value in our data storage. Type indefinite"
    
    __isvalue__ = True
    
    def set_key(self, key):
        self.key = key
    
    def __get__(self, instance, owner):
        valuedict = instance.__instdict__
        if valuedict:
            return valuedict[self.key]
        else: return self
            
    
    def __set__(self, instance, value):
        valuedict = instance.__instdict__
        valuedict[self.key] = value
    
    @staticmethod
    def validate():
        pass
