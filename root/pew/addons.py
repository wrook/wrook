#!python
# coding=UTF-8

# Inspired by Johannes Woolard
# Read original article at http://pytute.blogspot.com/2007/04/python-plugin-system.html

import re

class Handler():
	"""
	Sample for "meta":
	meta = {
		"id": "addScript",
		"description": "Adds the uservoice script to the page template",
		}
	
	Sample for "mappings":
	mappings =[
		"pew://templates.wrook.org/all/body-end"
		]
	
	"""
	meta = {} # Metadata for the handler
	data = {} # Inpout data of the request
	addon = None # Object reference to the handler which called the handler

	def __init__(self, addon):
		self.addon = addon
		self.init()

	def init(self):
		pass

	# Call to obtain a single text response
	def get(self):
		return "" 

	# Call to obtain a structured data response
	def data(self):
		return {}

class Addon():

	meta = {}
	handlers = []
	mappings = []
	defaultOptions = {}
	options = {}

	def __init__(self, data=None):
		if data:
			paramOptions = data["options"]
			self.options = {}
			if self.defaultOptions: self.options.extend(self.defaultOptions)
			if paramOptions: self.options.extend(paramOptions)
		self.init()

	def init(self):
		pass

	def parseMappings(self, scheme):
		# Standard types: pew, wsgi
		_mappings = []
		if scheme:
			for url, handler in self.mappings:
				if url.startswith("%s:" % scheme):
					_mappings += [(url[len(scheme)+1:], handler)]
		return _mappings

	def render(self, template_name="", template_dirs=[]):
		model = []

		import django_trans_patch as translation
		from jinja2 import Environment
		from jinja2 import FileSystemLoader
		from jinja2 import TemplateNotFound
		env = Environment(
			loader = FileSystemLoader(template_dirs),
			extensions=['jinja2.ext.i18n'])
		env.install_gettext_translations(translation)

		try: template = env.get_template(template_name)
		except TemplateNotFound: raise TemplateNotFound(template_name)
		return template.render(model)


class Addons():

	_addonMappings = []
	_addonMappingsCompiled = []
	_wsgiHandlers = []
	_selection = []
	matches = []
	addons = []

	def __init__(self):
		self._addonMappings = []
		self._addonMappingsCompiled = []
		self._wsgiHandlers = []
		self._selection = []
		self.matches = []
		self.addons = []
		self.baseFolder = ""

	def __call__(self, uri):
		""" Finds the matching handlers according to the addon uri requested. """
		handler = None
		groups = ()
		self.matches = []
		for regexp, handler_method, addon, compiled in self._addonMappingsCompiled:
			match = compiled.match(uri)
			if match:
				self.matches += [(handler_method, match.groups(), addon)]
		return self

	def addonMappings(self):
		return self._addonMappings
	
	def wsgiHandlers(self):
		return self._wsgiHandlers
	
	def load(self, folder, _baseFolder=None):
		import os.path
		import sys
		if not _baseFolder: _baseFolder = self.baseFolder
		addonpath = os.path.join(_baseFolder, "%s/" % folder)
		addonfolders = [fname for fname in os.listdir(addonpath) if os.path.isdir(os.path.join(addonpath, fname))]
		if not addonpath in sys.path:
		    sys.path.append(addonpath)
		imported_addons = []
		for name in addonfolders:
			imported_addons += [__import__(folder + "." + name, globals(), locals(), [name], -1)]
		for addon in imported_addons:
			addonInstance = addon.addon({})
			if addonInstance.meta:
				self.addons += [(
					addonInstance.meta["uri"],
					addonInstance.meta["version"],
					addonInstance
					)]
				
			wsgiHandlers = addonInstance.parseMappings("wsgi")
			if wsgiHandlers: self._wsgiHandlers += wsgiHandlers 

			addonMappings = addonInstance.parseMappings("pew")
			if addonMappings:
				addonMappings = [("pew:"+url, handler, addonInstance) for url, handler in addonMappings]
				# Add back the "pew:" prefix
				self._addonMappings += addonMappings
				self._addonMappingsCompiled += self.compile_mappings(addonMappings)

	def compile_mappings(self, handler_tuples):
		"""Initializes the maps needed for mapping urls to handlers and handlers to urls.
		Args:
			handler_tuples: list of (URI, RequestHandler) pairs.
		"""
		
#		handler_map = {}
#		pattern_map = {}
		url_mapping = []
		
		for regexp, handler, addon in handler_tuples:
			
#			handler_map[handler.__name__] = handler
			if not regexp.startswith('^'):
				regexp = '^' + regexp
			if not regexp.endswith('$'):
				regexp += '$'
			
			compiled = re.compile(regexp)
			url_mapping.append((regexp, handler, addon, compiled))
				
#			num_groups = len(RE_FIND_GROUPS.findall(regexp))
#			handler_patterns = pattern_map.setdefault(handler, [])
#			handler_patterns.append((compiled, num_groups))
			
#		self._handler_map = handler_map
#		self._pattern_map = pattern_map
#		self._addonMappings = url_mapping
		return url_mapping
	
	def get(self):
		""" Return the concatenated html of all addon responses. """
		content = ""
		if self.matches:
			for handler, args, addon in self.matches:
				if handler:
					handlerInstance = handler(addon)
					_content = handlerInstance.get()
					if _content: content += _content
		return content


