# -*- coding: utf-8 -*-

from routes import Mapper
from config import DEBUG

def get_map():
    " This function returns mapper object for dispatcher "
    map = Mapper()
    # Add routes here
    map.connect('index', '/', controller='controllers', action='index')
    #map.connect(None, '/route/url', controller='controllerName', action='actionName')


    if DEBUG:
        map.connect(None, '/static/{path_info:.*}', controller='static', action='index') #Handling static files

    return map

