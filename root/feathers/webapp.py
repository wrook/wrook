import os
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template, util

class Application(webapp.WSGIApplication):
	pass

def run(application):
	util.run_wsgi_app(application)

class RequestHandler(webapp.RequestHandler):
	Model = {}
	Template = ""
	TemplateBaseFolder = ""
	MasterTemplate = ""
	CurrentMember = None
	CurrentTheme = None
	CurrentLanguage = None
	AppConfig = None

	def setVisitedMember(self, member):
		if member:
			self.VisitedMember = member
			self.Model.update({"visitedMember": self.VisitedMember})
			selection = member.currentThemeSelection()
			if selection: self.setCurrentTheme(selection.Theme)

	def setCurrentTheme(self, theme):
		self.CurrentTheme = theme
		self.Model.update({"currentTheme":self.CurrentTheme})

	def render(self, templateFile=""):
		self.Model.update({"masterTemplate": self.MasterTemplate}) # Includes the path of the MasterTemplate in he model
		if templateFile != "": self.Template = templateFile #  If a template path is specified it overrides the one set previously
		path = os.path.join(self.TemplateBaseFolder, self.Template) # Merges the base folder and the template path
		templateText = template.render(path, self.Model) # Renders the template with the Model
		self.response.out.write(templateText) # Outputs the rendered template
	
	def getRender(self, templateFile=""): #Refactor: merge with render()
		self.Model.update({"masterTemplate": self.MasterTemplate}) # Includes the path of the MasterTemplate in he model
		if templateFile != "": self.Template = templateFile #  If a template path is specified it overrides the one set previously
		path = os.path.join(self.TemplateBase, self.Template) # Merges the base folder and the template path
		templateText = template.render(path, self.Model) # Renders the template with the Model
		return templateText # returns the rendered template

	def requestLogin(self):
		self.redirect("/Login") # Redirects to the standard URL for the Google Account login
