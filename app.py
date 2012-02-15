"""
Machinery for launching the wsgi server
"""
from config import URL_RESOLVER, CONTROLLERS, MIDDLEWARES, DEBUG, AUTO_RELOAD
from gevent import monkey, pywsgi
from gevent.wsgi import WSGIServer
from noodles.dispatcher import Dispatcher
from noodles.geventwebsocket.handler import WebSocketHandler
from noodles.http import Request, Response, Error500
from noodles.middleware import AppMiddlewares
from noodles.utils.mailer import MailMan
from noodles.websockserver import server
import logging
import sys
import os
import traceback
import re
import time
import threading
monkey.patch_all()


logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

resolver = __import__(URL_RESOLVER, globals(), locals())

# Create an dispatcher instance
dispatcher = Dispatcher(mapper=resolver.get_map(), controllers=CONTROLLERS)

# Load all midllewares for application
app_middlewares = AppMiddlewares(MIDDLEWARES)


# Our start point WSGI application
def noodlesapp(env, start_response):
    # Get request object
    request = Request(env)
    #print "Try to handle url_path '%s'" % request.path
    # Get callable object with routine method to handle request
    callable_obj = dispatcher.get_callable(request)
    if not callable_obj:
        # May be here an error,raise exception
        raise Exception('Can\'t find callable for this url path')
    # Callable function must return Respone object
    for middleware in app_middlewares:
        callable_obj = middleware(callable_obj)  # Hardcoded use of HTTP Session middleware
    try:
        response = callable_obj()
        return response(env, start_response)
    # Capture traceback here and send it if debug mode
    except Exception as e:
        f = logging.Formatter()
        traceback = f.formatException(sys.exc_info())
        # Don't remove this print
        print traceback  # Show traceback in console
        if DEBUG:
            response = Error500(e, traceback)
        else:
            response = Error500()
            MailMan.mail_send(MailMan(), e.__repr__(), traceback)
        return response(env, start_response)


def restart_program(mp, lck):
    print 'acquiring lock'
    acquired = lck.acquire(blocking=False)
    if not acquired:
        print 'failed to acquire'
        return None
    """Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function."""
    import commands
    import signal
    print 'deleting pyc'
    rmcmd = 'find %s -iname "*.pyc" -exec rm -rf {} \;' % mp
    st, op = commands.getstatusoutput(rmcmd)
    assert st == 0, "%s -> %s (%s)" % (rmcmd, op, st)
    python = sys.executable
    print 'executing %s %s' % (python, sys.argv)
    #os.execl(python, python, * sys.argv)
    os.spawnl(os.P_WAIT, python, python, *sys.argv)
    #os.execvp(python,**sys.argv)
    #os.kill(os.getpid(),signal.SIGINT)
    print 'executed'

    lck.release()
    print 'released lock'


class Observer(threading.Thread):
    def handler(self, arg1=None, arg2=None):
        print('event handled')  # %s ; %s'%(arg1,arg2))
        if hasattr(self, 'server_instance') and self.server_instance:
            print 'stopping server'
            self.server_instance.stop()
            del self.server_instance
            print 'done stopping'
        print 'restarting program'
        restart_program(self.mp, self.lck)
        print 'done restarting'

    def scanfiles(self, dr, files, checkchange=False, initial=False):
        goodfiles = ['.py']
        baddirs = ['site-packages', '.git', 'python(2|3)\.(\d+)', 'tmp']
        gfmatch = re.compile('(' + '|'.join(goodfiles) + ')$')
        bdmatch = re.compile('(\/)(' + '|'.join(baddirs) + ')($|\/)')
        walk = os.walk(dr)
        for w in walk:
            if bdmatch.search(w[0]):
                continue
            for fn in w[2]:
                if not gfmatch.search(fn):
                    continue
                ffn = os.path.join(w[0], fn)
                #print fn
                if ffn in files and initial:
                    raise Exception('wtf %s' % ffn)
                if not os.path.exists(ffn):
                    if not fn.startswith('.#'):
                        print ('%s does not exist' % ffn)
                    continue
                nmtime = os.stat(ffn).st_mtime
                if checkchange:
                    if (ffn not in files) or (nmtime > files[ffn]):
                        print 'change detected in %s' % ffn
                        return True
                files[ffn] = nmtime
        return False

    def run(self):
        files = {}
        self.scanfiles(self.mp, files, initial=True)
        print 'watching %s files' % len(files)
        while True:
            rt = self.scanfiles(self.mp, files, checkchange=True)
            if rt:
                self.handler()
            time.sleep(0.5)

    def fcntl_run(self):
        import fcntl
        import signal
        import threading
        import time
        print 'starting to watch events on %s' % self.mp
        signal.signal(signal.SIGIO, self.handler)
        fd = os.open(self.mp,  os.O_RDONLY)
        fcntl.fcntl(fd, fcntl.F_SETSIG, 0)
        fcntl.fcntl(fd, fcntl.F_NOTIFY,
                    fcntl.DN_MODIFY | fcntl.DN_CREATE | fcntl.DN_MULTISHOT)
        while True:
            time.sleep(0.1)
        print 'done watching events'


def fs_monitor(server_instance):
    o = Observer()
    o.lck = threading.Lock()
    o.mp = os.getcwd()
    o.server_instance = server_instance
    o.start()

# Start server function, you may specify port number here


def startapp():
    try:
        from config import PORT, SERVER_LOGTYPE
    except ImportError:
        PORT = 8088  # By defaultl 8088 debug port
    print 'Start server on %i...' % int(PORT)
    if SERVER_LOGTYPE == 'supress':
        import StringIO
        s = StringIO.StringIO()
    else:
        s = SERVER_LOGTYPE
    server_instance = server.WebSocketServer(('', int(PORT)), noodlesapp, log=s)
    if AUTO_RELOAD:
        fs_monitor(server_instance)
    server_instance.serve_forever()
