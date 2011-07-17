#!/usr/bin/env python
import sys, commands, os

current_dir = os.path.dirname(sys.argv[0])
template_dir = os.path.join(current_dir,'project_template')
op = sys.argv[1]
if op=='init':
    cmd = 'cp -r -i %s/* .' % (template_dir)
    st, op = commands.getstatusoutput(cmd)
    assert st == 0, "%s returned %s" % (cmd,st)
