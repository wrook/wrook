#!python
# coding=UTF-8

import pew.addons as addons

class Uservoice(addons.Addon):

	def init(self):
		self.meta = {
			"uri": "pew://uservoice.modules.wrook.org",
			"version": "1.0",
			"name": "Uservoice.com integration",
			"description": "Adds support for the customer feedback services of uservoice.com",
			"author": "Mathieu Sylvain",
			"url": "http://www.wrook.org",
			"optionsHelp": """
Options are:
- color: hex color code for the uservoice tab (without the dash sign)
- domain: domain name for your uservoice account (without http://)
- alignement: alignement (top, right, bottom or left)"""
			}
		self.mappings = [
			("pew://templates.wrook.org/all/body-end", script)
			]
		self.defaultOptions = {
			"color" : "F0F279",
			"domain" : "sitename.uservoice.com",
			"alignement" : "left"
			}
 
class script(addons.Handler):
	meta = {
		"title": "Uservoice script",
		"description": "Inserts the uservoice script to the page template",
		"uri": "/script"
		}

	def get(self):
		content = "<script src='http://%s/pages/general/widgets/tab.js?alignment=%s&amp;color=%s' type='text/javascript'></script>"
		return content % (
			self.addon.options.get("domain"),
			self.addon.options.get("alignement"),
			self.addon.options.get("color")
			)
