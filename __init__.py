# -*- coding: utf-8 -*-
from utils import maputils
from middleware import session
from websocket import wschannel, wsproxy
import sys

# Redefine modules names for backword capatibility
sys.modules['noodles.maputils'] = maputils
sys.modules['noodles.session'] = session
sys.modules['noodles.wschannel'] = wschannel
sys.modules['noodles.wsproxy'] = wsproxy