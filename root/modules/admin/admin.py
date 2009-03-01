#!python
# coding=UTF-8

#TODO: Refactor.... dependencies on app should be removed
import app
import pew.addons as addons

#Django imports for localization
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.utils import translation
from django.utils.translation import gettext as _
from django.conf import settings

from google.appengine.ext.db import djangoforms
from google.appengine.ext import db
from google.appengine.api import memcache

class AdminModule(addons.Addon):

	def init(self):
		self.meta = {
			"uri": "pew://admin.modules.wrook.org",
			"version": "1.0",
			"name": "Admin module",
			"description": "",
			"author": "Mathieu Sylvain",
			"homepage": "http://www.wrook.org",
			"optionsHelp": "",
			"description": "Administration console for wrook."
			}

		self.mappings = [
			( 'pew://navigation.wrook.org/main-menu', insert_link_in_main_menu),
			( 'wsgi:/SetDefaultTheme', set_default_theme),
			( 'wsgi:/admin/commands', AdminCommands), # Refactor: move to an admin module?
			(r'wsgi:/admin/commands/(.*)', AdminCommands), # Refactor: move to an admin module?
			( 'wsgi:/Test', Test),
			(r'wsgi:/admin', handler_admin),
			(r'wsgi:/admin/setup', handler_setup),
			(r'wsgi:/admin/setup/complete', handler_setup_complete)
			]


class insert_link_in_main_menu(addons.Handler):
	meta = {
		"title": "Insert link in main menu",
		"description": "Insert a link in the main menu pointing to the admin panel home"
		}
	def call(self, params=None, context=None):
		request = context
		if request.CurrentMember:
			if request.CurrentMember.isAdmin:
				return {
					"id": "mainMenu-Admin",
					"label": _("Admin"),
					"url": "/admin",
					"isSecondary": True
					}


#TODO: Refactor.... this should not need to be in this modules
class RequestHandler(app.RequestHandler):

	def get_template_directories(self):
		import os
		dirs = super(RequestHandler, self).get_template_directories()
		dirs += [os.path.join(os.path.dirname(__file__), "views")]
		return dirs

class CommandResult(db.Model):
	"""
	Result data from an admin command
	"""
	ErrorCode = db.IntegerProperty(default="0") # 0 = no errors
	Message = db.TextProperty(default="")

class AdminCommands(RequestHandler):
	def get(self):
		self.onRequest()
#		if self.CurrentMember:
		self.render('admin-commands.html')
#		else: self.requestLogin()

	def post(self, key):
		self.onRequest()
#		if self.CurrentMember:
		if (key == "doDefaultAllBookStatus"):
			operationResults = self.doDefaultAllBookStatus()
		if (key == "doDefaultAllChapterNumberTo0"):
			operationResults = self.doDefaultAllChapterNumberTo0()
		if (key == "doLoadLicenseTypes"):
			operationResults = self.doLoadLicenseTypes()
		if (key == "doSetEncryptionKey"):
			operationResults = self.doSetEncryptionKey()
		else:
			operationResults = CommandResult(ErrorCode=1, Message=_("No commands have been processed. Missing parameters!"))
		self.Model.update({"operationResults": operationResults})
		self.render('admin-commands.html')
#		else: self.requestLogin()
	
	def doDefaultAllBookStatus(self):
		for book in Book.all():
			if book.Stage == "planning": book.Stage = "writing"
			for chapter in book.Chapters:
				if chapter.Stage == "planning": chapter.Stage = "writing"
				chapter.put()
			book.put()
		result = CommandResult(ErrorCode=0, Message=_("Empty status properties of all books and chapters have been defaulted!"))
		return result
	
	def doSetEncryptionKey(self):
		appConfig = getWrookAppConfig()
		appConfig.EncryptionKey = self.request.get("encryptionKey")
		appConfig.put()
		result = CommandResult(ErrorCode=0, Message=_("The new encryption key has been set!"))
		return result
	
	def doLoadLicenseTypes(self):
		import licensing
		licensing.LoadLicenseTypes()
		result = CommandResult(ErrorCode=0, Message=_("All license types have been loaded into the database!"))
		return result
	
	def doDefaultAllChapterNumberTo0(self):
		for chapter in Chapter.all():
			chapter.Number=0
			chapter.put()
		result = CommandResult(ErrorCode=0, Message=_("All chapter numbers have been reseted to 0!"))
		return result

class insert_admin_menu(addons.Handler):
	meta = {
		"title": "Insert admin menu",
		"description": "Insert menu items for the admin section.",
		"uri": "/insert_admin_menu"
		}

	def get(self):
		html = self.addon.render("panels-aboutWrook2.html", self.get_template_directories())
		return html

	#TODO: Refactor... duplicate in the request handler		
	def get_template_directories(self):
		import os
		dirs = []
		dirs += [os.path.join(os.path.dirname(__file__), "views")]
		return dirs


class Test(RequestHandler):
	def get(self):
		import _runtest
		self.response.out.write(_runtest.getTestResults())

class set_default_theme(RequestHandler): 
	meta = {
		"title": "Set default theme",
		"description": "Service page to sets the default theme for the the whole site."
		}
	#TODO: Refactor -  Move back to the Customize module
	def get(self):
		from feathers import customize
		self.onRequest()
		if self.CurrentMember:
			theme = customize.Theme.get(self.request.get("selectedTheme"))
			if theme and self.CurrentMember.isAdmin:
				db.delete(app.Moment.all().filter("isDefault =", True)) # Removes the current default moments
				moment = app.Moment(
					Title = "Default moment",
					Theme = theme,
					isDefault = True
					)
				moment.put()
				memcache.delete("wrookDefaultTheme") # Invalidates the cached default theme
				self.redirect("/Themes")
			else: self.error(500)
		else: self.requestLogin()



class SetupForm(djangoforms.ModelForm):
	'''
	Form used to do the initial setup
	'''
	class Meta:
		model = app.WrookAppConfig
		fields = (
			"SiteName",
			"SiteTagline",
			"SiteDescription",
			"SiteAdminEmail",
			"SiteAdminName",
			"EncryptionKey"
			)



class handler_admin(RequestHandler):
	meta = {
		"title": "Admin home",
		"description": "Home of the administrative console.",
		"url": "/admin"
		}
	def get(self):
		self.onRequest(isSetup=True)
		self.Model.update({
			})
		self.render("home.html")

class handler_setup(RequestHandler):
	meta = {
		"title": "Setup",
		"description": "Basic setup screen for the site.",
		"url": "/admin/setup"
		}
	def get(self):
		self.onRequest(isSetup=True)
		wrookAppConfig = app.getWrookAppConfig(flushCache=True, createIfNone=True)
		form = SetupForm(instance=wrookAppConfig)
		self.Model.update({
			"form": form
			})
		self.render("setup.html")
	
	def post(self):
		self.onRequest(isSetup=True)
		wrookAppConfig = app.getWrookAppConfig(flushCache=True, createIfNone=True)

		form = SetupForm(data=self.request.POST, instance=wrookAppConfig)
		if form.is_valid():
			# Save the form, and redirect to the view page
			entity = form.save(commit=False)
			entity.SetupComplete = True
			entity.put()
			wrookAppConfig = app.getWrookAppConfig(flushCache=True, createIfNone=True)
			self.redirect("/admin/setup/complete")
		else:
			self.Model.update({
				"form": form
				})
			self.render("setup.html")

class handler_setup_complete(RequestHandler):
	meta = {
		"title": "Setup completed",
		"description": "Page shown once setup has been completed.",
		"url": "/admin/setup/complete"
		}
	def get(self):
		self.onRequest(isSetup=True)
		self.render("setup-complete.html")


