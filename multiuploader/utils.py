import os
import time
import urllib
import logging
import mimetypes

from hashlib import sha1
from random import choice
from wsgiref.util import FileWrapper

from django.conf import settings
from django.core.files import File
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.timezone import now
from django.utils.text import get_valid_filename
from django.core.files.uploadedfile import UploadedFile


import multiuploader.default_settings as DEFAULTS

log = logging


# Getting files here
def format_file_extensions(extensions):
    return ".(%s)$" % "|".join(extensions)


def _upload_to(instance, filename):
    upload_path = getattr(settings, 'MULTIUPLOADER_FILES_FOLDER', DEFAULTS.MULTIUPLOADER_FILES_FOLDER)

    if upload_path[-1] != '/':
        upload_path += '/'

    filename = get_valid_filename(os.path.basename(filename))
    filename, ext = os.path.splitext(filename)
    hash = sha1(str(time.time())).hexdigest()
    fullname = os.path.join(upload_path, "%s.%s%s" % (filename, hash, ext))
    return fullname


def get_uploads_from_request(request):
    """Description should be here"""
    attachments = []
    #We're only supports POST
    if request.method == 'POST':
        if request.FILES == None:
            return []

        #getting file data for further manipulations
        if not u'files' in request.FILES:
            return []
        
        for fl in request.FILES.getlist("files"):
            wrapped_file = UploadedFile(fl)
            filename = wrapped_file.name
            file_size = wrapped_file.file.size
            attachments.append({"file": fl, "date": now(), "name": wrapped_file.name})
        
    return attachments

def get_uploads_from_temp(ids):
    """Method returns of uploaded files"""

    from models import MultiuploaderFile

    ats = []
    files = MultiuploaderFile.objects.filter(pk__in=ids)
    
    #Getting THE FILES

    for fl in files:
        ats.append({"file":File(fl.file), "date":fl.upload_date, "name":fl.filename})
        
    return ats

def get_uploads_from_model(instance, attr):
    """Replaces attachment files from model to a given location, 
       returns list of opened files of dict {file:'file',date:date,name:'filename'}"""
    
    ats = []
    files = getattr(instance, attr)

    for fl in files.all():
        ats.append({"file": File(fl.file), "date": fl.upload_date, "name": fl.filename})
            
    return ats

def generate_safe_pk(self):
    def wrapped(self):
        while 1:
            skey = getattr(settings, 'SECRET_KEY', 'asidasdas3sfvsanfja242aako;dfhdasd&asdasi&du7')
            pk = sha1('%s%s' % (skey, ''.join([choice('0123456789') for i in range(11)]))).hexdigest()
           
            try:
                self.__class__.objects.get(pk=pk)
            except:
                return pk	

    return wrapped

def download_response(request, filelike, filename):
    response = StreamingHttpResponse(filelike)

    type, encoding = mimetypes.guess_type(filename)

    response['Content-Type'] = type or 'application/octet-stream'
    response['Content-Length'] = filelike.size
    if encoding is not None:
        response['Content-Encoding'] = encoding

    # To inspect details for the below code, see http://greenbytes.de/tech/tc2231/
    if u'WebKit' in request.META['HTTP_USER_AGENT']:
        # Safari 3.0 and Chrome 2.0 accepts UTF-8 encoded string directly.
        filename_header = 'filename=%s' % filename.encode('utf-8')
    elif u'MSIE' in request.META['HTTP_USER_AGENT']:
        # IE does not support internationalized filename at all.
        # It can only recognize internationalized URL, so we do the trick via routing rules.
        filename_header = ''
    else:
        # For others like Firefox, we follow RFC2231 (encoding extension in HTTP headers).
        filename_header = 'filename*=UTF-8\'\'%s' % urllib.quote(filename.encode('utf-8'))

    response['Content-Disposition'] = 'attachment; ' + filename_header

    return response