# -*- coding: utf-8 -*-
from noodles.http import Response

def index(request):
    return Response('<h1>Hello, NoodlesFramework!</h1>')
