# -*- coding: utf-8 -*-
import re, logging, copy
import redis

non_record = re.compile(r'__\w+__')

REDIS_CONN = redis.Redis()

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


class Model(object):
    " General class for objects description in data storage "
    # static model parameters
    __structure__ = {}
    __collection__ = {} # Collection name for Mongo DB
    
    id = Value(int)
    
    def __init__(self, valuedict=None, embedded=False, **kwargs):
        classname = self.__class__.__name__
        
        self.__init_structure__(classname, valuedict, **kwargs)
        
        self.collection_name = self.__collection__[classname]
        
        storage = kwargs.get('storage')
        if not storage: self.storage = 'redis'
        
        #self.id = None
        self.embedded = embedded
        self.save_routines = {'redis': self.save_redis, 'mongo': self.save_mongo}
        #self.load_routines = {'redis': self.load_redis, 'mongo': self.load_mongo}
    
    def __init_structure__(self, classname, valuedict=None, **kwargs):
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
    
    def save(self, storage = None):
        if self.embedded:
            logging.warning('You should save embedded objects with high level object')
            return
        if not storage: storage = self.storage
        save_to_storage = self.save_routines.get(storage)
        if save_to_storage: save_to_storage()
        else:
            raise Exception('Where is no such storage %s!' % storage)
        
    # Save to Redis storage
    def save_redis(self):
        " Save object to redis storage"
        if not self.id:
            new_id = REDIS_CONN.incr(self.__class__.__name__.lower() + '_key')
            self.id = new_id
        self.save_redis_recursive(':'.join([self.collection_name, str(self.id)]), self.__instdict__)
                
    def save_redis_recursive(self, redis_key, valuedict):
        " Recursive save instance dictionary to Redis storage"
        for k in valuedict:
            if type(valuedict[k]) != dict:
                curr_key = ':'.join([redis_key, k])
                REDIS_CONN.set(curr_key, valuedict[k])
            else:
                self.save_redis_recursive(':'.join([redis_key, k]), valuedict[k])
    
    # Save to Mongo
    def save_mongo(self):
        pass
    
    @classmethod
    def get_structure(cls):
        structure = cls.__structure__.get(cls.__name__)
        if not structure:
            # Structure of the class is not created yet
            cls_inst = cls()
            return cls.__structure__.get(cls.__name__)
        return structure
    
    @classmethod
    def get_collection_name(cls):
        classname = cls.__name__
        collection_name = cls.__collection__.get(classname)
        if not collection_name:
            cls.__collection__[classname] = classname.lower() + 's'
            return cls.__collection__[classname]
        return collection_name
    
    def get_values(self):
        return copy.deepcopy(self.__instdict__)
    
    @classmethod
    def get(cls, **kwargs):
        " Get one instance from storage"
        storage = kwargs.get('storage')
        if not storage: storage = self.storage
        
        if storage == "redis":
            if kwargs.has_key('id'):
                return cls.get_redis(kwargs['id'])
            else:
                 #raise Exception('Current storage is redis, so you must search by id key')
                 return None
        elif storage == "mongo":
            pass
        #load_from_storage = self.load_routines.get(storage)
        #if load_from_storage: load_from_storage(**kwargs)
        #else:
        #    raise Exception('Load model data. No such storage')
    
    @classmethod
    def load_redis_recursive(cls, instance_dict, obj_key):
        for k in instance_dict:
            if type(instance_dict[k]) != dict:
                instance_dict[k] = REDIS_CONN.get(':'.join([obj_key, k]))
            else:
                cls.load_redis_recursive(instance_dict[k], ':'.join([obj_key, k]))
                
    
    @classmethod
    def get_redis(cls, id):
        "Get object from Redis storage by ID"
        # First try to find object by Id
        inst_id = REDIS_CONN.get(':'.join([cls.get_collection_name(), str(id), 'id']))
        if not inst_id: # No objects with such ID
            raise
        else:
            # Copy structure of Class to new dictionary
            instance_dict = copy.deepcopy(cls.get_structure())
            obj_key = ':'.join([cls.get_collection_name(), str(id)])
            # Fullfill instance dictionary by values from Redis storage
            cls.load_redis_recursive(instance_dict, obj_key)
            # return class instance with values is instance_dict
            return cls(valuedict = instance_dict)
        
        
    def load(self, **kwargs):
        pass
        
    def load_redis(**kwargs):
        
        pass

    def load_mongo(self):
        pass

    
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
