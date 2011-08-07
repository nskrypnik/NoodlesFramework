'''
filedesc: request dispatch logic
'''
from noodles.http import Error404
from noodles.templates import Templater 
import sys, os

# Add standard controllers dir to PYTHON_PATH directory
sys.path.append( os.path.join(os.path.dirname(__file__), 'controllers') )

class CallWrapper(object):
    def __init__(self, controller, action, extra_args):
        self.extra_args = extra_args
        self.request = self.extra_args['request'] # for middleware compatibility
        try:
            self.action = getattr(controller, action)
        except AttributeError:
            raise Exception('No such action in controller %s' % controller.__name__)
        
    def __call__(self):
        return self.action(**self.extra_args)

class Dispatcher(object):
    def __init__(self, **kwarg):
        # Get the mapper object
        mapper = kwarg.get('mapper')
        if mapper: self.mapper = mapper
        else: raise Exception('No mapper object')
        controllers = kwarg.get('controllers')
        if not controllers:
            raise Exception('No controllers specified for application')
        self.controllers = {}
        for controller in controllers:
            # TODO: Enhance import logic here to import controllers like mod1.mod2
            # Import all controllers
            base_mod = __import__(controller, globals(), locals())
            mod = sys.modules.get(controller)
            if not mod: mod = base_mod
            self.controllers[controller] = mod
        #add some default controllers
        self.controllers[Templater._name] = Templater()

    def get_callable(self, request):
        " Returns callable object "
        route_res = self.mapper.match(request.path)
        if not route_res: return self.not_found(request)
        # Get controller name and action from routes
        controller_name = route_res.get('controller')
        action = route_res.get('action')
        
        controller = self.controllers.get(controller_name)
        if not controller: raise Exception('No such controller \'%s\'' % controller_name)

        # Prepare extra args for callable
        extra_args = route_res.copy() # copying all data from routes dictionary
        # Delete controller and action items
        del extra_args['controller']; del extra_args['action']
        extra_args['request'] = request

        callable_obj = CallWrapper(controller, action, extra_args)
        return callable_obj

    def not_found(self, request):
        " Returns pair if url does'nt match any choice in mapper " 
        class NotFoundCallable():
            
            def __init__(self, request):
                self.request = request
            
            def __call__(self):
                " Genereate 404 server response here "
                return Error404('<h1>Error 404. Can\'t find page</h1>')
        
        return NotFoundCallable(request)
