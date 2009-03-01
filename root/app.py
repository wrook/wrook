#!python
# coding=UTF-8

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings
from google.appengine.ext import db
#from django.utils import translation
import django_trans_patch as translation
from django.utils.translation import gettext as _
from google.appengine.ext import webapp as googleWebapp
from feathers import webapp


#TODO: Having the picnikKey here is not secure, put in the app config
picnikKey = "eb44efec693047ac4f4b2a429bc0be5a" # Developper Key for the Picnik API


def URLMappings():
	return [('/.*', handler_http404)]

class Application(googleWebapp.WSGIApplication):

	_addons = None

	def __init__(self, url_mapping, debug=False, addons=None):
		joined_url_mapping = []
		if addons:
			self._addons = addons
			joined_url_mapping += addons.wsgiHandlers()
		joined_url_mapping += url_mapping

		super(Application, self).__init__(joined_url_mapping, debug=False)

	def addons(self):
		return self._addons


class RequestHandler(webapp.RequestHandler):

	def render(self, template_name=""):
		self.MasterTemplate = self.MasterTemplate2
		self.render2(template_name)

	def onRequest(self, isSetup=False):
		'''
		Initialization method triggered before a request is processed.
		'''
		import os
		import datetime
		import random
		from feathers import membership

		self.Model = {}

		self.application = Application.active_instance
		self.addons = self.application.addons()
		#Set current execution context of addons to the currrent request
		self.addons.context = self;

		#Store the current environment in the model (ex.: google or dev)
		environ = getEnvironment()

		# Add model data needed before the appConfig
		self.Model.update({
			"environment" : environ,
			"addons" : self.addons
			})

		config = getWrookAppConfig()

		# Load the application config from the database and attach it to the request
		# If a valid and completed config cant be found, the user is sent to the initial setup

		if config:
			self.AppConfig = config
			if config.SetupComplete:
		
				#TODO: Figure out if this should be somewhere else than in the global scope
#				webapp.currentRequest = self

				# Use to reference the ongoing request without having to do injection
				self.MasterTemplate = os.path.join(os.path.dirname(__file__), "views/template-main-e.html") # Sets the default template to be used by hosted modules
				self.MasterTemplateStylesheets = os.path.join(os.path.dirname(__file__), "views/stylesheets.html") # Sets the default template to be used by hosted modules
				self.MasterTemplateScripts = os.path.join(os.path.dirname(__file__), "views/scripts.html") # Sets the default template to be used by hosted modules
				self.TemplateBase = os.path.join(os.path.dirname(__file__), "views/template-main.html") # Sets the default template to be used by hosted modules
				self.MasterTemplate2 = "template-main-e2.html"
				self.TemplateBase2 = "template-main-e2.html" # Sets the default template to be used by hosted modules
				self.CurrentMember = membership.loginFromCookies(self) # Load the current member from the google authentication and add it to the requesthandler
				self.CurrentTheme = getDefaultTheme() # Set the default theme as the current theme
				if self.CurrentMember: translation.activate(self.CurrentMember.PreferedLanguage) # If the is a current member, his prefered language is activated
				else: translation.activate("en") # If not, the default language is set to english
				self.Model.update({
					'random': random.random(),
					'templateMain': self.MasterTemplate,
					'templateMain2': self.MasterTemplate2,
					'templateScripts': self.MasterTemplateScripts,
					'templateStylesheets': self.MasterTemplateStylesheets,
					'templateBase': self.TemplateBase,
					'templateBase2': self.TemplateBase2,
					'now': datetime.datetime.now(), # Add the current time to the model
					'currentMember': self.CurrentMember, # Add the current user to the model
					'currentTheme': self.CurrentTheme, # Add the default theme to the model
					'appConfig': self.AppConfig, # Add the app config to the model
					'application': self.application
					})
				return
		if not isSetup:
			self.redirect("/admin/setup")


class WrookAppConfig(db.Model):
	'''
	Configuration object for the Wrook application.
	'''
	#TODO:Could this entity be renamed to simply "config"
#	import books
	#TODO: Refactor so that there is no need to import books (move DefaultCover elsewhere) 
#	DefaultCover = db.ReferenceProperty(books.Cover, verbose_name=_("Default cover"))
	SetupComplete = db.BooleanProperty(default=False, verbose_name=_("Setup is complete"))
	SiteName = db.StringProperty(verbose_name=_("Site name"))
	SiteTagline = db.StringProperty(verbose_name=_("Tagline"))
	SiteDescription = db.TextProperty(verbose_name=_("Short description"))
	SiteAdminEmail = db.StringProperty(verbose_name=_("Administrator email"))
	SiteAdminName = db.StringProperty(verbose_name=_("Administrator name"))
	EncryptionKey = db.StringProperty(verbose_name=_("Encryption key")) # Used when a scecret key is needed for 

def getEnvironment():
	import os
	environment = {
		"isGoogle" : os.environ['SERVER_SOFTWARE'].startswith('Google'),
		"isDevelopment" : os.environ['SERVER_SOFTWARE'].startswith('Development')
		}
	return environment

def getDefaultTheme():
	from google.appengine.api import memcache
	from feathers import customize
	#TODO: Refactor -  Move back to the Customize module??
	defaultTheme = memcache.get("wrookDefaultTheme")
	if not defaultTheme:
		defaultMoments = customize.Moment.all().filter("isDefault =", True).order("-Priority").fetch(limit=1)
		if len(defaultMoments)==0:
			return None
		else:
			defaultTheme = defaultMoments[0].Theme
			memcache.add("wrookDefaultTheme", defaultTheme)
	return defaultTheme

def getWrookAdmin():
	from feathers import membership
	wrookAppConfig = getWrookAppConfig()
	admin = membership.Member.all().filter("Email =", wrookAppConfig.SiteAdminEmail).filter("isAdmin =", True).fetch(limit=1)
	if len(admin)==1:
		return admin[0]
	else:
		return None

def getWrookAppConfig(flushCache=False, createIfNone=False):
	'''
	Obtain the application configuration currently in effect.
	'''
	from google.appengine.api import memcache
	if flushCache: wrookAppConfig = None
	else: wrookAppConfig = memcache.get("wrookAppConfig")
	if not wrookAppConfig:
		cfg = WrookAppConfig.all().fetch(limit=1)
		if len(cfg) > 0:
			wrookAppConfig = cfg[0]
			memcache.add("wrookAppConfig", wrookAppConfig)
		elif createIfNone:
			wrookAppConfig = WrookAppConfig()
			wrookAppConfig.put()
			memcache.add("wrookAppConfig", wrookAppConfig)
	return wrookAppConfig

class handler_http404(RequestHandler):
	def get(self):
		self.onRequest(self)
		self.error(404)
		self.Model.update({
			})
		self.render2('views/http404.html')

def handle_exception(requestHandler, exception, debug_mode):
	import cgi
	import sys
	import traceback
	import jsonpickle
	from feathers import utils
	if not debug_mode:
		trace = ''.join(traceback.format_exception(*sys.exc_info()))
		try:
			trace = trace + "\n\n\nRequest state:\n" + jsonpickle.encode(requestHandler)
		except:
			trance = trace + "\n\n\nState request unavailable" 
#		requestHandler.onRequest()
		requestHandler.CurrentTheme = None
		requestHandler.error(500)
		requestHandler.Model.update({
				"currentTheme": None,
				"trace": utils.text_to_linebreaks(trace)
			})
		requestHandler.render2('views/http500.html')
	else:
		super(requestHandler, exception, debug_mode)

