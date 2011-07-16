
try:
    from django.core.handlers.wsgi import WSGIHandler
except:
    raise Exception('Can\' import Django WSGIHandler. Have you installed django?')
    
def run_django(request):
    return WSGIHandler()
