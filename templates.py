# Here we implement mako templating for our server

from mako.template import Template
from mako.lookup import TemplateLookup
from noodles.http import Response
from config import TEMPLATE_DIRS, MAKO_TMP_DIR
import os

# Specify application lookup
appLookup = TemplateLookup(directories=TEMPLATE_DIRS,
                module_directory=MAKO_TMP_DIR, output_encoding='utf-8', input_encoding='utf-8')

def render_to_response(templatename, context, request = None):
    if request:
        context['request'] = request
    template = appLookup.get_template(templatename)
    rendered_page = template.render(**context)
    return Response(rendered_page)

def render_to_string(templatename, context, request = None):
    " Just renders template to string "
    if request:
        context['request'] = request
    template = appLookup.get_template(templatename)
    rendered_page = template.render(**context)
    return rendered_page

# Specify the render_to decorator
# Usage - some thing like this
#
#   @render_to
#   def index(request):
#       # some code
#       return some_dict # Dictionary with context variables
#
def render_to(templatename):
    def renderer(func):
        def wrapper(**kwargs):
            # Get context from the handler function
            context = func(**kwargs)
            # Add some extra values to context
            context['request'] = kwargs['request'] # while it's enough :)
            # Get a tamplate object by the template name
            template = appLookup.get_template(templatename)
            rendered_page = template.render(**context)
            return Response(rendered_page)
        return wrapper
    return renderer
