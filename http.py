# Module for extending webob Request and Response classes
# to use in our server application
import webob
import json

class Request(webob.Request):
    " Request object wrapper fo adding session handling and other features "
    def __init__(self, env, start_response):
        super(Request, self).__init__(env, start_response)

class BaseResponse(webob.Response):
    " Just wrapper, may be implemnt cookies there, may be somthing else )) "
    pass

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
        raise NotImplemented

class Error404(BaseResponse):
    " Simple Http 404 error implementation "
    def __init__(self, error_body=''):
        super(Error404, self).__init__()
        self.status = 404
        self.headerlist = [('Content-type', 'text/html')]
        self.charset = 'utf-8'
        self.body = error_body

class XResponse(BaseResponse):
    " Ajax response, return a JSON object "
    def __init__(self, response_dict):
        # Set standard response attributes
        super(XResponse, self).__init__()
        self.status = 200 # 200 OK, it's default, but anyway...
        self.headerlist = [('Content-type', 'application/x-javascript')]
        self.charset = 'utf-8'
        self.body = json.dumps(response_dict)

class WebSocket():
    """
        Object for Web Socket handling.
        Get an function f parameter. f is function that get an
        server socket instance ws and handle data from it
    """
    def __init__(self, f):
        self.handler = f
    
    def __call__(self, env, start_response):
        start_response('200 OK',[('Content-Type','application/json')])
        ws = env.get('socketio')
        # TODO: create Error object
        if not ws: raise Exception('No server socket instance!')
        self.handler(ws)

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
