# -*- coding: utf-8 -*-

import redis
try:
    from config import REDIS_HOST
except ImportError:
    REDIS_HOST = 'localhost'
    

RedisConn = redis.Redis(REDIS_HOST)