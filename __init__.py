# -*- coding: utf-8 -*-
from utils import maputils
from middleware import session
import sys

# Redefine modules names for backword capatibility
sys.modules['noodles.maputils'] = maputils
sys.modules['noodles.session'] = session
