#!python
# coding=UTF-8

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.ext import db
#from django.utils import translation
import django_trans_patch as translation
from django.utils.translation import gettext as _

#TODO: Having the picnikKey here is not secure, put in the app config
picnikKey = "eb44efec693047ac4f4b2a429bc0be5a" # Developper Key for the Picnik API

class Moment(db.Model):
	'''
	A moment according to the system.
	
	Moments define periodes of the year where specific customization of the site occurs
	These moments can change de default, the palette, special messages to the user
	'''
	from feathers import customize
	Title = db.StringProperty()
	Begins = db.DateTimeProperty()
	Ends = db.DateTimeProperty()
	Created = db.DateTimeProperty(auto_now_add=True)
	Theme = db.ReferenceProperty(customize.Theme, collection_name=_("Moments"))
	isDefault = db.BooleanProperty(default=False)
	Priority = db.IntegerProperty(required=True, default=0)

class WrookAppConfig(db.Model):
	'''
	Configuration object for the Wrook application.
	'''
	#TODO:Could this entity be renamed to simply "config"
	import books
	DefaultCover = db.ReferenceProperty(books.Cover, verbose_name=_("Default cover"))
	EncryptionKey = db.StringProperty(verbose_name=_("Encryption key")) # Used when a scecret key is needed for encrypting passwords and other data

def onRequest(self):
	'''
	Initialization method triggered before a request is processed.
	'''
	import os
	import datetime
	from feathers import webapp
	from feathers import membership

	#TODO: Figure out if this should be somewhere else than in the global scope
	webapp.currentRequest = self
	# Use to reference the ongoing request without having to do injection
	self.Model = {}
	self.MasterTemplate = os.path.join(os.path.dirname(__file__), "views/template-main-d.html") # Sets the default template to be used by hosted modules
	self.TemplateBase = os.path.join(os.path.dirname(__file__), "views/template-main.html") # Sets the default template to be used by hosted modules
	self.TemplateBase2 = os.path.join(os.path.dirname(__file__), "views/template-main2.html") # Sets the default template to be used by hosted modules
	self.CurrentMember = membership.loginFromCookies(self) # Load the current member from the google authentication and add it to the requesthandler
	self.CurrentTheme = getDefaultTheme() # Set the default theme as the current theme
	self.AppConfig = getWrookAppConfig() # Load the application config from the database
	if self.CurrentMember: translation.activate(self.CurrentMember.PreferedLanguage) # If the is a current member, his prefered language is activated
	else: translation.activate("en") # If not, the default language is set to english
	self.Model.update({
		'templateMain': self.MasterTemplate,
		'templateBase': self.TemplateBase,
		'now': datetime.datetime.now(), # Add the current time tot the model
		'currentMember': self.CurrentMember, # Add the current user to the model
		'currentTheme': self.CurrentTheme, # Add the default theme to the model
		'appConfig': self.AppConfig # Add the app config to the model
		})

def getDefaultTheme():
	from google.appengine.api import memcache
	#TODO: Refactor -  Move back to the Customize module??
	defaultTheme = memcache.get("wrookDefaultTheme")
	if not defaultTheme:
		defaultMoments = Moment.all().filter("isDefault =", True).order("-Priority").fetch(limit=1)
		if len(defaultMoments)==0:
			return None
		else:
			defaultTheme = defaultMoments[0].Theme
			memcache.add("wrookDefaultTheme", defaultTheme)
	return defaultTheme

def getWrookAppConfig():
	'''
	Obtain the application configuration currently in effect.
	'''
	from google.appengine.api import memcache
	wrookAppConfig = memcache.get("wrookAppConfig")
	if not wrookAppConfig:
		cfg = WrookAppConfig.all().fetch(limit=1)
		if len(cfg) == 1:
			wrookAppConfig = cfg[0]
			memcache.add("wrookAppConfig", wrookAppConfig)
	return wrookAppConfig
