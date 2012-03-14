# -*- coding: utf-8 -*-
'''
filedesc: a kind of redis orm
'''

from noodles.redisconn import RedisConn

import re
import logging
import copy
import json
import os
import hashlib


def mkey(*params):
    """return a key composed of the arguments passed, delimeted by colon. for usage with redis"""
    rt = ":".join([str(rt) for rt in params])
    return rt

non_record = re.compile(r'__\w+__')
from config import *
try:
    from config import REDIS_NAMESPACE
except ImportError:
    current_path = os.getcwd()
    current_dir = os.path.split(current_path)[-1]
    REDIS_NAMESPACE = current_dir.lower().replace(' ', '_')


class DoesNotExist(Exception):
    pass


class Value(object):
    "Single value in our data storage"

    __isvalue__ = True

    def __init__(self, type_of_value=None):
        if type_of_value:
            self.type = type_of_value
        else:
            self.type = str

    def set_key(self, key):
        self.key = key

    def typing(self, value):
        " If value is None it returns None, else value value in proper type"
        if value != None:
            return self.type(value)
        else:
            return None

    def get_default(self):
        return None

    def __get__(self, instance, owner):
        valuedict = instance.__instdict__
        if valuedict:
            return self.typing(valuedict[self.key])
        else:
            return self

    def __set__(self, instance, value):
        valuedict = instance.__instdict__
        try:
            valuedict[self.key] = self.type(value)
        except:
            logging.info('could not save key %s with value %s as type %s' % (self.key, value, self.type))
            raise


class DateValue(Value):
    "Represents datatime python object"
    pass


class Model(object):
    " General class for objects description in data storage "
    # static model parameters
    __structure__ = {}
    __collection__ = {}  # Collection name for Mongo DB
    id = Value(str)
    __salt__ = None

    def __init__(self, valuedict=None, embedded=False, expire=None, **kwargs):

        #we might use salt to make our sequence key for this object more interesting
        if 'salt' in kwargs:
            self.__salt__ = kwargs['salt']
        self.expire = expire
        classname = self.__class__.__name__
        self.__init_structure__(classname, valuedict, **kwargs)
        self.collection_name = self.__collection__[classname]
        self.embedded = embedded

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
            if k == 'salt':
                continue
            elif k in self.__instdict__:
                if hasattr(kwargs[k], 'get_values'):
                    self.__instdict__[k] = kwargs[k].get_values()
                else:
                    self.__instdict__[k] = kwargs[k]
            else:
                raise Exception('There is no such value \'%s\' in %s model.' % (k, classname))

    def save(self, storage=None):
        " Save object to redis storage"
        if self.embedded:
            logging.warning('You should save embedded objects with high level object')
            return
        if not self.id:
            new_id = RedisConn.incr(mkey(REDIS_NAMESPACE, self.__class__.__name__.lower() + '_key'))
            if self.__salt__:
                self.id = hashlib.md5(str(new_id) + self.__salt__).hexdigest()
            else:
                self.id = new_id
#        print mkey(REDIS_NAMESPACE, self.collection_name, self.id), json.dumps(self.__instdict__)
        RedisConn.set(mkey(REDIS_NAMESPACE, self.collection_name, self.id), json.dumps(self.__instdict__))
        if self.expire != None:
            RedisConn.expire(mkey(REDIS_NAMESPACE, self.collection_name, self.id), self.expire)
        #self.save_redis_recursive(mkey(self.collection_name, self.id), self.__instdict__)

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
    def get(cls, id, storage=None, salt=None):  # storage=None for backword capability
        "Get object from Redis storage by ID"
        if salt:
            idtoget = hashlib.md5(id + salt).hexdigest()
        else:
            idtoget = id
        # First try to find object by Id
        # example: gameserver:scratchgames:101
        inst_data = RedisConn.get(mkey(REDIS_NAMESPACE, cls.get_collection_name(), idtoget))
        if not inst_data:  # No objects with such ID
            raise DoesNotExist('No model in Redis srorage with such id')
        else:
            # Copy structure of Class to new dictionary
            instance_dict = json.loads(inst_data.__str__())
            return cls(valuedict=instance_dict)

    @classmethod
    def delete(cls, id, storage=None):  # storage=None for backword capability
        "Delete key specified by ``id``"
        result = RedisConn.delete(mkey(REDIS_NAMESPACE, cls.get_collection_name(), id))
        return result

    #return flag to update client cookie
    def update(self, storage=None, **kwargs):  # storage=None for backword capability
        '''update time expire'''
        print 'updating::'
        id = mkey(REDIS_NAMESPACE, self.collection_name, self.id)

        if 'expire' in kwargs:
            print TIME_TO_OVERWRITE_CLIENT_COOKIE, RedisConn.ttl(id)
            if  TIME_TO_OVERWRITE_CLIENT_COOKIE > RedisConn.ttl(id):
                result = RedisConn.expire(id, kwargs['expire'])
                logging.info('UPDATE LIFETIME TO: %s SECONDS' % kwargs['expire'])
                return result
            else:
                logging.debug('non_update_SESSION')

        else:
            raise Exception('unknown action!!!')
        
        
    @classmethod
    def exists(cls, id, storage=None):  # storage=None for backword capability
        return RedisConn.exists(mkey(REDIS_NAMESPACE, cls.get_collection_name(), id))


class Node(Value):
    " Use it for embedd objects to model "

    def __init__(self, model_class):
        self.model = model_class

    def __get__(self, instance, owner):
        valuedict = instance.__instdict__
        if valuedict:
            # TODO: Optimiize this!
            model_inst = self.model(valuedict=valuedict[self.key])
            return model_inst
        else:
            return self

    def __set__(self, instance, value):
        pass

    def get_default(self):
        model_inst = self.model()
        return model_inst.get_structure()
