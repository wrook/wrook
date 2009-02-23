#!python
# coding=UTF-8

#TODO: Refactor.... dependencies on app should be removed
import app 
import pew.addons as addons

class AddonsManagement(addons.Addon):

	def init(self):
		self.meta = {
			"uri": "pew://plugins.modules.wrook.org",
			"version": "0.1",
			"name": "Addons management module",
			"description": "A module to manage all addons.",
			"author": "Mathieu Sylvain",
			"url": "http://www.wrook.org",
			}
		self.mappings = [
			( 'wsgi:/Addons', handler_addons)
			]


#TODO: Refactor.... this should not need to be in this modules
class RequestHandler(app.RequestHandler):

	def get_template_directories(self):
		import os
		dirs = super(RequestHandler, self).get_template_directories()
		dirs += [os.path.join(os.path.dirname(__file__), 'views')]
		return dirs

class handler_addons(RequestHandler):
	meta = {
		"title": "Manage Addons",
		"description": "Manage the list of all addons available.",
		"url": "/Addons"
		}

	def get(self):
		#TODO: refactor... the onRequest call should not be necessary
		self.onRequest(self)
		self.render("addons.html")

