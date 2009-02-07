#!python
# coding=UTF-8

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from google.appengine.ext import webapp

class Application(webapp.WSGIApplication):
	pass

def run(application):
	from google.appengine.ext.webapp import util
	util.run_wsgi_app(application)

def render(template_name, model):
	import django_trans_patch as translation
	from jinja2 import Environment
	from jinja2 import FileSystemLoader
	from jinja2 import TemplateNotFound
	template_dirs = [
		os.path.dirname(__file__),
		os.path.join(os.path.dirname(__file__), 'views'),
		os.path.join(os.path.dirname(__file__), '..'),
		os.path.join(os.path.dirname(__file__), '../views')]
	env = Environment(
		loader = FileSystemLoader(template_dirs),
		extensions=['jinja2.ext.i18n'])
	env.install_gettext_translations(translation)
	try: template = env.get_template(template_name)
	except TemplateNotFound: raise TemplateNotFound(template_name)
	return template.render(model)

class RequestHandler(webapp.RequestHandler):
	Model = {}
	Template = ""
	TemplateBaseFolder = ""
	MasterTemplate = ""
	CurrentMember = None
	CurrentTheme = None
	CurrentLanguage = None
	AppConfig = None

	def raise_http404(self):
		self.error(404)
		self.Model.update({})
		self.render2('views/http404.html')


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
		from google.appengine.ext.webapp import template
		self.Model.update({"masterTemplate": self.MasterTemplate}) # Includes the path of the MasterTemplate in he model
		if templateFile != "": self.Template = templateFile #  If a template path is specified it overrides the one set previously
		path = os.path.join(self.TemplateBaseFolder, self.Template) # Merges the base folder and the template path
		templateText = template.render(path, self.Model) # Renders the template with the Model
		self.response.out.write(templateText) # Outputs the rendered template
	
	def getRender(self, templateFile=""): #Refactor: merge with render()
		from google.appengine.ext.webapp import template
		self.Model.update({"masterTemplate": self.MasterTemplate}) # Includes the path of the MasterTemplate in he model
		if templateFile != "": self.Template = templateFile #  If a template path is specified it overrides the one set previously
		path = os.path.join(self.TemplateBaseFolder, self.Template) # Merges the base folder and the template path
		templateText = template.render(path, self.Model) # Renders the template with the Model
		return templateText # returns the rendered template

	def render2(self, template_name=""):
		self.Model.update({"masterTemplate": self.MasterTemplate}) # Includes the path of the MasterTemplate in he model
		self.response.out.write(render(template_name, self.Model))

	def requestLogin(self, comeback=None):
		self.redirect("/Login?comeback=%s" % comeback)
