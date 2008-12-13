#!python
# coding=UTF-8

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import cgi
import datetime
import logging
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from feathers import webapp
from feathers import membership
from feathers import utils

def URLMappings():
	return [
		('/Proforma/Confirm', Confirm),
		('/Proforma/Success', Success),
		('/Proforma/Failed', Failed),
		('/Proforma/Warning', Warning)
	]

def onRequest(request): # Event triggering to let the host application intervene
	pass

class ProformaPage(object):
	Model = {}
	RequestHandler = None
	BaseURL = ""

	def url(self):
		url = self.BaseURL + "?"
		i = 0
		for key, value in self.Model.items():
			if i > 0: url = url + "&"
			url = url + key + "=" + value
			i = i + 1
		return url

class Confirm(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		self.Model.update({
			'statement': self.request.get("statement"), # The statement to confirm
			'redirect': self.request.get("redirect") # The page to where you must redirect upon confirmation
			})
		self.TemplateBaseFolder = os.path.dirname(__file__)
		self.render('views/proforma-confirm.html')

confirmPage = ProformaPage()
confirmPage.RequestHandler=Confirm
confirmPage.BaseURL="/Proforma/Confirm"

class Success(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		self.Model.update({
			'statement': self.request.get("Statement"), # The statement to confirm
			'continueURL': self.request.get("ContinueURL"), # The URL to where the user is invited to continue 
			'continueLabel': self.request.get("ContinueLabel") # The Label of the "continue" button 
			})
		self.TemplateBaseFolder = os.path.dirname(__file__)
		self.render('views/proforma-success.html')

class SuccessPage(ProformaPage):
	RequestHandler = Success
	BaseURL = "/Proforma/Success"

class Failed(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		self.Model.update({
			'statement': self.request.get("statement"), # The statement to confirm
			'continueURL': self.request.get("redirect"), # The URL to where the user is invited to continue 
			'continueLabel': self.request.get("redirect"), # The Label of the "continue" button 
			'backURL': self.request.get("redirect"), # The URL to where the user is invited to go back 
			'backLabel': self.request.get("redirect"), # The Label of the "go back" button 
			'retryURL': self.request.get("redirect"), # The URL to where the user is invited to retry his last action 
			'retryLabel': self.request.get("redirect") # The Label of the "retry" button 
			})
		self.TemplateBaseFolder = os.path.dirname(__file__)
		self.render('views/proforma-failed.html')

failedPage = ProformaPage()
failedPage.RequestHandler=Failed
failedPage.BaseURL="/Proforma/Failed"

class Warning(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		self.Model.update({
			'statement': self.request.get("statement"), # The statement to confirm
			'continueURL': self.request.get("redirect"), # The URL to where the user is invited to continue 
			'continueLabel': self.request.get("redirect"), # The Label of the "continue" button 
			'backURL': self.request.get("redirect"), # The URL to where the user is invited to go back 
			'backLabel': self.request.get("redirect") # The Label of the "go back" button 
			})
		self.TemplateBaseFolder = os.path.dirname(__file__)
		self.render('views/proforma-warning.html')

warningPage = ProformaPage()
warningPage.RequestHandler=Warning
warningPage.BaseURL="/Proforma/Warning"

