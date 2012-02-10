# -*- coding: utf-8 -*-
'''
filedesc: Module for session support. There is HTTP session, standard http concept. We can use it with Web Socket session together
'''

from noodles.datastore import Model, Value, DoesNotExist
from noodles.middleware import BaseMiddleware
try:
    from config import SESSION_COOKIE
except:
    SESSION_COOKIE = 'hsess_id'
import json
import logging


class SessionData(Model):
    data = Value(str)


class Session():

    class _Data(object):
        def init(self, _dict_=None):
            if _dict_:
                self.__dict__.update(_dict_)

        def update(self, _dict_):
            self.__dict__.update(_dict_)

        def __setattr__(self, name, value):
            " Validate here values to set"
            if type(value) not in [int, float, str, dict, bool]:
                raise ValueError('The type of session data value must be int, float, str, dict or bool')
            else:
                self.__dict__[name] = value

        def __getattr__(self, name):
            return None

        def __repr__(self):
            return "Session Data: %s" % self.__dict__.__repr__()

    def __init__(self, id=None):
        self.id = None
        self.data = self._Data()
        if id:
            try:
                self._sessdata = SessionData.get(id=id)
                self.id = self._sessdata.id
                self.data.update(json.loads(self._sessdata.data))
                return
            except DoesNotExist:
                pass
        self._sessdata = SessionData()
        self._sessdata.data = '{}'
        self._sessdata.save()
        self.id = self._sessdata.id
        self.data.update(json.loads(self._sessdata.data))

    def save(self):
        self._sessdata.data = json.dumps(self.data.__dict__)
        self._sessdata.save()


class SessionMiddleware(BaseMiddleware):
    "Middleware that handles HTTP sessions"

    def __call__(self):

        if not hasattr(self.request, 'session'):
            # Get from cookie HTTP session ID
            sess_id = self.request.str_cookies.get(SESSION_COOKIE)

            self.request.session = Session(sess_id)
            response = self.callable()
            if hasattr(response, 'is_noodles_response') and sess_id != self.request.session.id:
                # callable returns native noodlse Response object
                # let's update it cookies
                response.set_cookie(SESSION_COOKIE, str(self.request.session.id))
            self.request.session.save()
            return response
