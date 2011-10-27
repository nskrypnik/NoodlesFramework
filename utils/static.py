'''
filedesc: Controller for serving static content
'''
import os
from noodles.http import BaseResponse, Error404


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

    '.wav': 'audio/x-wav',
    '.mp3': 'audio/mpeg',
    '.ogg': 'audio/ogg',

    # And much more...
    # Add mime types from this source http://en.wikipedia.org/wiki/Internet_media_type
    # Thank you Jimmy
    }

def toInt(val):
    if val == '': return 0
    return int(val)


def index(request, path_info, path):
    parital_response = False
    path_info = path_info.replace('%28', '(').replace('%29', ')').replace('%20', ' ')
    response = BaseResponse()
    # define a file extansion
    base, ext = os.path.splitext(path_info) # Get the file extansion
    mime_type = MIME_TYPES.get(ext, 'text/plain')
    if not mime_type: raise Exception("unknown doc, or something like that :-P: %s" % ext)
    static_file_path = os.path.join(path, path_info)
    # Check if this path exists
    if not os.path.exists(static_file_path):
        error_msg = "<h1>Error 404</h1> No such file STATIC_ROOT/%s" % path_info
        return Error404(error_msg)
    # configure response
    static_file = open(static_file_path, 'rb') # Open file
    # Here we try to handle Range parameter

    content_offset = 0
    content_end = 0
    request_range = request.headers.get('Range')
    if request_range:
        range_bytes = request_range.replace('bytes=', '')
        range_bytes = range_bytes.split('-')
        if len(range_bytes) > 2: raise Exception('Wrong http Range parameter "%s"' % request_range)
        content_offset = toInt(range_bytes[0])
        content_end = toInt(range_bytes[1])
        parital_response = True


    static_content = static_file.read()
    if content_end <= 0 or content_end >= len(static_content): content_end = len(static_content) - 1
    response.body = static_content[content_offset: content_end + 1]


    response.charset = 'utf-8'

    if parital_response:
        response.status = 206
        response.headerlist = [('Content-type', mime_type),
        ('Content-Range', 'bytes %i-%i/%i' % (content_offset, content_end, len(static_content)))]

    else:
        response.headerlist = [('Content-type', mime_type)]

    # This seems to be clear, return this response object

    return response
