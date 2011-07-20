# -*- coding: utf-8 -*-

def urlmap(map, url_rules):
    " Util for make url rules easy "
    for rule in url_rules:
        url_pattern, controller_dot_action = rule
        controller, action = controller_dot_action.split('.')
        
        map.connect(None, url_pattern, controller = controller, action = action)