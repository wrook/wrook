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
			"enabledByDefault": True,
			}
		self.mappings = [
			( "pew://admin.wrook.org/menu", insert_link_in_admin_menu),
			( "wsgi:/admin/addons/list", handler_addons)
			]


#TODO: Refactor.... this should not need to be in this modules
class RequestHandler(app.RequestHandler):

	def get_template_directories(self):
		import os
		dirs = super(RequestHandler, self).get_template_directories()
		dirs += [os.path.join(os.path.dirname(__file__), 'views')]
		return dirs


class insert_link_in_admin_menu(addons.Handler):
	meta = {
		"title": "Insert link in admin menu",
		"description": "Insert a link in the admin menu pointing to the addons management"
		}
	def call(self, params=None, context=None):
		return {
			"id": "addons",
			"label": _("Addons"),
			"sectionId": "addons",
			"items": ({
				"id": "addons-installed",
				"label": _("Installed addons"),
				"url": "/admin/addons/list",
				"sectionId": "addons-installed"
				},{
				"id": "addons-getMore",
				"label": _("Get more addons"),
				"url": "/admin/addons/get-more",
				"sectionId": "addons-getMore"
				})
			}

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

