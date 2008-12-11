#!python
# coding=UTF-8

from feathers import webapp

def URLMappings():
	return [
		( '/About/OpenSourceAttribution', open_source_attribution),
		( '/About/OpenSourceLicense', open_source_license),
		( '/About/CPAL', CPAL),
		( '/About/Who', who),
		( '/About/Half-Baked-Edition', half_baked_edition)]

class half_baked_edition(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-halfBakedEdition.html")

class open_source_license(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-openSourceLicense.html")

class open_source_attribution(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-openSourceAttribution.html")

class CPAL(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-CPAL.html")

class who(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-who.html")

