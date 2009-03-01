#!python
# coding=UTF-8

#TODO: Refactor.... dependencies on app should be removed
import app 
import pew.addons as addons

class AboutPlugin(addons.Addon):

	def init(self):
		self.meta = {
			"uri": "pew://about.modules.wrook.org",
			"version": "1.0",
			"name": "About module of wrook.org",
			"description": "",
			"author": "Mathieu Sylvain",
			"homepage": "http://www.wrook.org",
			"optionsHelp": "",
			"description": "Series of pages describing what the current site is about."
			}

		self.mappings = [
			( "pew://join.membership.module.wrook.org/sidebar", sidebar_panel),
			( "pew://login.membership.module.wrook.org/sidebar", sidebar_panel),
			( "pew://visitor.home.module.wrook.org/sidebar", sidebar_panel),
			( "wsgi:/About/OpenSourceAttribution", open_source_attribution),
			( "wsgi:/About/OpenSourceLicense", open_source_license),
			( "wsgi:/About/CPAL", CPAL),
			( "wsgi:/About/Who", who),
			( "wsgi:/About/Half-Baked-Edition", half_baked_edition)
			]

class sidebar_panel(addons.Handler):

	meta = {
		"title": "Sidebar panel",
		"description": "Sibebar panel with link to the about mobule.",
		"uri": "/sidebarPane"
		}

	def get(self, params=None, context=None):
		html = self.addon.render("panels-aboutWrook2.html", self.get_template_directories())
		return html

	#TODO: Refactor... duplicate in the request handler		
	def get_template_directories(self):
		import os
		dirs = []
		dirs += [os.path.join(os.path.dirname(__file__), "views")]
		return dirs

#TODO: Refactor.... this should not need to be in this modules
class RequestHandler(app.RequestHandler):

	def get_template_directories(self):
		import os
		dirs = super(RequestHandler, self).get_template_directories()
		dirs += [os.path.join(os.path.dirname(__file__), "views")]
		return dirs

class half_baked_edition(RequestHandler):
	meta = {
		"title": "Half Baked Edition",
		"description": "Details on the unfinished nature of the wrook project.",
		"url": "/About/Half-Baked-Edition"
		}
	def get(self):
		#TODO: refactor... the onRequest call should not be necessary
		self.onRequest(self)
		self.render("about-halfBakedEdition.html")

class open_source_license(RequestHandler):
	meta = {
		"title": "Open Source License",
		"description": "Information about the open source nature of wrook and how it can be used.",
		"url": "/About/OpenSourceLicense"
		}
	def get(self):
		#TODO: refactor... the onRequest call should not be necessary
		self.onRequest(self)
		self.render("about-openSourceLicense.html")

class open_source_attribution(RequestHandler):
	meta = {
		"title": "Open source attribution",
		"description": "Information about the open source attribution necessary when reusing wrook's code.",
		"url": "/About/OpenSourceAttribution"
		}
	def get(self):
		#TODO: refactor... the onRequest call should not be necessary
		self.onRequest(self)
		self.render("about-openSourceAttribution.html")

class CPAL(RequestHandler):
	meta = {
		"title": "CPAL 1.0 License",
		"description": "The full text of the CPAL 1.0 license",
		"url": "/About/CPAL"
		}
	def get(self):
		#TODO: refactor... the onRequest call should not be necessary
		self.onRequest(self)
		self.render("about-CPAL.html")

class who(RequestHandler):
	meta = {
		"title": "Who is behing wrook",
		"description": "Information about who is managing and building the wrook project.",
		"url": "/About/Who"
		}
	def get(self):
		#TODO: refactor... the onRequest call should not be necessary
		self.onRequest(self)
		self.render("about-who.html")


