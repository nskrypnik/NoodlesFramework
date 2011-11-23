"""
filedesc: mako templating for our server
"""
from config import TEMPLATE_DIRS, MAKO_TMP_DIR
from mako.lookup import TemplateLookup
from noodles.http import Response
from operator import isCallable
import config

# Specify application lookup
appLookup = TemplateLookup(directories=TEMPLATE_DIRS,
               module_directory=MAKO_TMP_DIR, output_encoding='utf-8',
               input_encoding='utf-8')


class ContextManager(object):
    """
    ContextManager class. Use contextManager object to manage your
    application context
    """
    def __new__(cls):
        if '_inst' not in vars(cls):
            cls._inst = object.__new__(cls)
            return cls._inst

    def __init__(self):
        self.context_processors = []
        self.context_constants = {}

    def add_processor(self, func):
        """
        Add context processor function to generate general context
        Func function must return dictionary of context variables
        """
        self.context_processors.append(func)

    def add_constants(self, constants):
        " Add dictionary of constant template variables "
        self.context_constants.update(constants)

    def update_context(self, context, request=None):
        # Add request and config objects to context
        if request:
            context['request'] = request
        context['config'] = config

        # Update context by constants
        context.update(self.context_constants)

        # Update context by context processors
        for processor in self.context_processors:
            c = processor(request)
            context.update(c)

contextManager = ContextManager()


def render_to_response(templatename, context, request=None):
    rendered_page = render_to_string(templatename, context, request)
    return Response(rendered_page)


def render_to_string(templatename, context, request=None):
    " Just renders template to string "
    contextManager.update_context(context, request)
    template = appLookup.get_template(templatename)
    rendered_page = template.render(**context)
    return rendered_page


class Templater(object):
    " Used for direct_to_template function realization, see maputils "
    _name = '__direct_templater'

    @staticmethod
    def render(request, templatename, **kwargs):
        rendered_page = render_to_string(templatename, kwargs, request)
        return Response(rendered_page)


###############################################################################
# Specify the render_to decorator
# Usage - some thing like this
#
#   @render_to
#   def index(request):
#       # some code
#       return some_dict # Dictionary with context variables
###############################################################################
def render_to(templatename):
    def renderer(func):
        def wrapper(**kwargs):
            # Get context from the handler function
            context = func(**kwargs)
            if isCallable(context):
                return context
            # Add some extra values to context
            request = kwargs['request']  # while it's enough :)
            rendered_page = render_to_string(templatename, context, request)
            return Response(rendered_page)
        return wrapper
    return renderer
