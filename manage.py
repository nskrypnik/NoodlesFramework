#!/usr/bin/env python
import sys,commands,os
mydir = os.path.dirname(sys.argv[0])
tpldir = os.path.join(mydir,'project_template')
op = sys.argv[1]
if op=='init':
    cmd = 'cp -r -i %s/* .'%(tpldir)
    st,op = commands.getstatusoutput(cmd)
    assert st==0,"%s returned %s"%(cmd,st)
