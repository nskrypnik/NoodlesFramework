# -*- coding: utf-8 -*-
# Module for extending webob Request and Response classes
# to use in our server application

from mako.template import Template

import webob
import json
import logging


SET_COOKIES = '__set_cookies'
UNSET_COOKIES = '__unset_cookies'

class Request(webob.Request):
    " Request object wrapper fo adding session handling and other features "
    def __init__(self, env):
        super(Request, self).__init__(env)

class BaseResponse(webob.Response):
    " Just wrapper, may be implemnt cookies there, may be somthing else )) "
    is_noodles_response = True # for check if it really noodles response

class Response(BaseResponse):
    " Simple response class with 200 http header status "
    def __init__(self, body = ''):
        super(Response, self).__init__()
        # Set standard response attributes
        self.status = 200 # 200 OK, it's default, but anyway...
        self.headerlist = [('Content-type', 'text/html')]
        self.charset = 'utf-8'
        self.body = body

class Redirect(BaseResponse):
    " Redirect response "
    def __init__(self, redirect_url):
        super(Redirect, self).__init__()
        self.status = 301
        self.headerlist = [('Content-type', 'text/html')]
        self.charset = 'utf-8'
        self.location = redirect_url

class Error404(BaseResponse):
    " Simple Http 404 error implementation "
    def __init__(self, error_body=''):
        super(Error404, self).__init__()
        self.status = 404
        self.headerlist = [('Content-type', 'text/html')]
        self.charset = 'utf-8'
        self.body = error_body
        
class DebugError500(BaseResponse):
    "HTTP 500 error response with server traceback"
    def __init__(self, ex, tb):
        super(DebugError500, self).__init__()
        self.status = 500
        self.headerlist = [('Content-type', 'text/html')]
        self.charset = 'utf-8'
        tb = '<br />'.join(tb.split('\n'))
        error_500_template = """
                            <h1>Internal Noodles error</h1>
                            <div style="font-size:125%"> 
                                ${ex} 
                            </div>
                            
                            <div style="margin-top: 20px">
                                ${tb}
                            </div>
                            """
        
        self.body = Template(error_500_template).render(ex = ex.__repr__(), tb = tb).encode('utf-8')

class XResponse(BaseResponse):
    " Ajax response, return a JSON object "
    def __init__(self, response_dict):
        # Set standard response attributes
        super(XResponse, self).__init__()
        self.status = 200 # 200 OK, it's default, but anyway...
        self.headerlist = [('Content-type', 'application/x-javascript')]
        self.charset = 'utf-8'
        
        # Set and unset cookies
        # Set cookies
        set_cookies_dict = response_dict.get(SET_COOKIES)
        logging.debug('response_dict is %s. Set-cookies dict is %s' % (response_dict, set_cookies_dict))
        if set_cookies_dict:
            for cookie in set_cookies_dict:
                logging.debug('Try to set cookie %s to value %i' % (cookie, set_cookies_dict[cookie]))
                self.set_cookie(cookie, str(set_cookies_dict[cookie]))
            response_dict.pop(SET_COOKIES)
        
        # Unset cookies
        unset_cookies_dict = response_dict.get(UNSET_COOKIES)
        if unset_cookies_dict:
            for cookie in unset_cookies_dict:
                self.delete_cookie(cookie)
            response_dict.pop(UNSET_COOKIES)
        
        
        
        self.body = json.dumps(response_dict)

class WebSocket():
    """
        Object for Web Socket handling.
        Get an function f parameter. f is function that get an
        server socket instance ws and handle data from it
    """
    def __init__(self, f, *args, **kwargs):
        self.handler = f
        self.args = args
        self.kwargs = kwargs
    
    def __call__(self, env, start_response):
        start_response('200 OK',[('Content-Type','application/json')])
        #print env
        get_websocket = env.get('wsgi.get_websocket')
        ws = get_websocket()
        ws.do_handshake()
        # TODO: create Error object
        if not ws: raise Exception('No server socket instance!')
        self.handler(ws, *self.args, **self.kwargs)

# Specify decorator for ajax response controller functions
# Usage:
#
#   @ajax_response
#   def some_controller(request):
#       # some code
#       return resonse_dict # dictionary object with response values
def ajax_response(func):
    def gen(**kwargs):
        resp_dict = func(**kwargs)
        return XResponse(resp_dict)
    return gen

def websocket(func):
    def gen(request, *args, **kwargs):
        return WebSocket(func, *args, **kwargs)
    return gen
