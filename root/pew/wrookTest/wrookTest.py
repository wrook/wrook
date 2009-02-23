#!python
# coding=UTF-8

import app

class TestPlugin(app.Module):
	
	def register(self, registrationData={}):
		wsgiHandlers = [
			( '/test/test/', handler_test)
			]
		return {
			"wsgiHandlers" : wsgiHandlers
			}
		

class handler_test(app.RequestHandler):
	def get(self):
		self.response.out.write("Success!")
