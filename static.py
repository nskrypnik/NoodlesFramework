"Controller for static content"
import os
from noodles.http import BaseResponse, Error404
from config import STATIC_ROOT

# Mime types dictionary, contain pairs: key - file extansion,
# value - mime type
MIME_TYPES = {
    # Application types
    '.swf': 'application/x-shockwave-flash',
    
    # Text types
    '.gz':'application/x-tar',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.html': 'text/html',
    '.txt': 'text/plain',
    '.xml': 'text/xml',
    # Image types
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.png': 'image/png',
    '.tiff': 'image/tiff',
    
    # Sound files
    
    'wav': 'audio/x-wav',
    
    # And much more...
    # Add mime types from this source http://en.wikipedia.org/wiki/Internet_media_type
    # Thank you Jimmy
    }

def index(request, path_info):
    path_info = path_info.replace('%28', '(').replace('%29', ')').replace('%20', ' ')
    response = BaseResponse()
    # define a file extansion
    base, ext = os.path.splitext(path_info) # Get the file extansion
    mime_type = MIME_TYPES.get(ext)
    if not mime_type: raise Exception("unknown doc, or something like that :-P")
    static_file_path = os.path.join(STATIC_ROOT, path_info)
    # Check if this path exists
    print 'static_file_path:', static_file_path
    if not os.path.exists(static_file_path):
        # TODO: return Error404 
        error_msg = "<h1>Error 404</h1> No such file STATIC_ROOT/%s" % path_info
        return Error404(error_msg)
    # configure response
    static_file = open(static_file_path, 'rb') # Open file
    response.body = static_file.read()
    response.headerlist = [('Content-type', mime_type)]
    response.charset = 'utf-8'
    # This seems to be clear, return this response object
    return response
