# To enable doctests to run from TextMate, import this module
# (Use only when testing, then comment out.)
# From: http://groups.google.com/group/google-appengine/browse_thread/thread/fa81f6abd95aa8b9/efed988b302aafb4?lnk=gst&q=duncan+doctests#efed988b302aafb4
# Via Aral Balkan's blog: http://aralbalkan.com/1358

import sys, os
sys.path = sys.path + [
	'/Python25/Lib/site-packages',
	'/Python25/Lib/site-packages/epydoc',
	'/Program Files/Google/google_appengine',
	'/Program Files/Google/google_appengine/lib/django',
	'/Program Files/Google/google_appengine/lib/webob',
	'/Program Files/Google/google_appengine/lib/yaml/lib',
	'/Program Files/Google/google_appengine/google/appengine',
	'/wrook/root/latest/',
	'/wrook/root/latest/root']

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub
from google.appengine.api import mail_stub
from google.appengine.api import urlfetch_stub
from google.appengine.api import user_service_stub
 
APP_ID = u'test_app'
AUTH_DOMAIN = 'gmail.com'
LOGGED_IN_USER = ''  # set to '' for no logged in user
 
# Start with a fresh api proxy.
apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
 
# Use a fresh stub datastore.
stub = datastore_file_stub.DatastoreFileStub(APP_ID, '/dev/null', '/dev/null')
apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)
 
# Use a fresh stub UserService.
apiproxy_stub_map.apiproxy.RegisterStub('user',user_service_stub.UserServiceStub())
os.environ['AUTH_DOMAIN'] = AUTH_DOMAIN
os.environ['USER_EMAIL'] = LOGGED_IN_USER
 
# Use a fresh urlfetch stub.
apiproxy_stub_map.apiproxy.RegisterStub('urlfetch', urlfetch_stub.URLFetchServiceStub())

# Use a fresh mail stub.
apiproxy_stub_map.apiproxy.RegisterStub('mail', mail_stub.MailServiceStub())
 