# -*- coding: utf-8 -*-
import re, logging, copy

non_record = re.compile(r'__\w+__')

class Model(object):
    " General class for objects description in data storage "
    # static model parameters
    __structure__ = {}
    __collection__ = {} # Collection name for Mongo DB
    
    def __init__(self, valuedict=None, embedded=False, **kwargs):
        classname = self.__class__.__name__
        # create dictionary for model instance
        self.__instdict__ = {}
        # Check static model structure
        if not self.__structure__.get(classname):
        # if not - create it
            self.__structure__[classname] = {}
            # Specify the collection name
            self.__collection__[classname] = classname.lower() + 's'
            logging.debug('Creating structure for model %s' % (classname))
            # Browse model for properties
            for key in dir(self):
                if not non_record.match(key):
                    value = getattr(self, key)
                    if hasattr(value, '__isvalue__'):
                        value.set_key(key)
                        self.__structure__[classname][key] = value.get_default()
        if valuedict:
            self.__instdict__ = valuedict
        else:
            self.__instdict__ = copy.deepcopy(self.__structure__[classname])
        
        for k in kwargs:
            if k in self.__instdict__:
                if hasattr(kwargs[k], 'get_values'):
                    self.__instdict__[k] = kwargs[k].get_values()
                else:
                    self.__instdict__[k] = kwargs[k]
            else:
                raise Exception('There is no such value \'%s\' in %s model.' % (k, classname))
    
    def get_structure(self):
        classname = self.__class__.__name__
        return self.__structure__.get(classname)
    
    def get_collection_name(self):
        classname = self.__class__.__name__
        return self.__collection__[classname]
    
    def get_values(self):
        return copy.deepcopy(self.__instdict__)
        
    def load(self):
        pass
    
    def save(self):
        pass
                 

class Value(object):
    "Single value in our data storage"
    
    __isvalue__ = True
    
    def __init__(self, type_of_value = None):
        if type_of_value: self.type = type_of_value
        else: self.type = str
    
    def set_key(self, key):
        self.key = key
    
    def typing(self, value):
        " If value is None it returns None, else value value in proper type"
        if value: return self.type(value)
        else: return None
    
    def get_default(self):
        return None
    
    def __get__(self, instance, owner):
        valuedict = instance.__instdict__
        if valuedict:
            return self.typing(valuedict[self.key])
        else: return self        
    
    def __set__(self, instance, value):
        valuedict = instance.__instdict__
        valuedict[self.key] = self.type(value)
    
class Node(Value):
    " Use it for embedd objects to model "
    
    def __init__(self, model_class):
        self.model = model_class
    
    def __get__(self, instance, owner):
        valuedict = instance.__instdict__
        if valuedict:
            # TODO: Optimiize this!
            model_inst = self.model(valuedict = valuedict[self.key])
            return model_inst
        else: return self
    
    def __set__(self, instance, value):
        pass
    
    def get_default(self):
        model_inst = self.model()
        print self.model
        return model_inst.get_structure()

