"""
This is the App Engine Console auto-executing module.  When you start a console session, it will
execute "from autoexec import *".  So you may place anything in here which you find useful.
"""

# Examples:  Uncomment these if you want them in your console by default.
#
#from google.appengine.ext import db
#from google.appengine.api import users
#import logging

# This allows you to run help(...) just like the standard console has.
import site
help = site._Helper()
del site
