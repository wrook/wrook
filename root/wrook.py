#!python
# coding=UTF-8
'''
Wrook's main module
'''

#Feathers imports
from feathers import stories
from feathers import utils
from feathers import customize
from feathers import membership
from feathers import proforma
from feathers import talk
from feathers import webapp # Still necessary here for the exception handling class

#Import static wrook modules
import app
import books
import members

def hook_modules(URLMappings):
	# Integrate the admin module
	URLMappings += books.URLMappings()
	books.onRequest = app.RequestHandler.onRequest
	# Integrate the stories module
	URLMappings += stories.URLMappings()
	stories.onRequest = app.RequestHandler.onRequest
	# Integrates the Customize module
	URLMappings += customize.URLMappings()
	customize.onRequest = app.RequestHandler.onRequest
	# Integrates the Membership module
	URLMappings += membership.URLMappings()
	membership.onRequest = app.RequestHandler.onRequest
	# Integrates the Membership module
	URLMappings += proforma.URLMappings()
	proforma.onRequest = app.RequestHandler.onRequest
	# Integrate the Talk module
	URLMappings += talk.URLMappings()
	talk.onRequest = app.RequestHandler.onRequest
	# Integrate the Members module
	URLMappings += members.URLMappings()
	#members.onRequest = app.RequestHandler.onRequest
	webapp.RequestHandler.handle_exception = app.handle_exception
	# Integrate the main App module
	URLMappings += app.URLMappings()
	return URLMappings

def real_main():
	'''
	The basic main function to start the application
	on the production servers
	'''
	application = start_application()
	run(application)

def firepython_main():
	'''
	The basic main function to start the application
	on the production servers
	'''
	application = start_application()
	from firepython.middleware import FirePythonWSGI
	run(FirePythonWSGI(application))

def profile_log_main():
	'''
	Main function used for profiling to the log files.
	'''
	#TODO: Find a way to send the profiler log results to FirePython
	import cProfile
	import logging
	import pstats
	import StringIO

	application = start_application()
	prof = cProfile.Profile()
	prof = prof.runctx("real_main()", globals(), locals())
	stream = StringIO.StringIO()
	stats = pstats.Stats(prof, stream=stream)
	stats.sort_stats("cumulative")  # Or cumulative
	stats.print_stats(150)  # 80 = how many to print
	logging.info("Profile data:\n%s", stream.getvalue())

def profile_html_main():
	'''
	This is the main function for profiling to the html output
	'''
	import cProfile, pstats
	application = start_application()
	prof = cProfile.Profile()
	prof = prof.runctx("real_main()", globals(), locals())
	print "<div style='text-align:left;font-size:1.1em; color: #000; background: #fff; padding: 20px;'><pre>"
	stats = pstats.Stats(prof)
	#stats.sort_stats("time")  # Or cumulative
	stats.sort_stats("cumulative")  # Or cumulative
	stats.print_stats(300)  # 80 = how many to print
	print "</pre></div>"

def profile_firepython_main():
	'''
	This is the main function for pushing profiling data up to firepythoin
	'''
	import cProfile
	import logging
	import pstats
	import StringIO

	application = start_application()
	prof = cProfile.Profile()
	prof = prof.runctx("firepython_main()", globals(), locals())
	stream = StringIO.StringIO()
	stats = pstats.Stats(prof, stream=stream)
	stats.sort_stats("cumulative")  # Or cumulative
	stats.print_stats(100)  # 80 = how many to print
	logging.info("Profile data:\n%s", stream.getvalue())

def start_application():
	'''
	Instanciate the application object and its addons
	'''
	import os
	import pew.addons
	URLMappings = hook_modules([])
	# Load addons from the modules and plugins folders
	addons = pew.addons.Addons()
	addons.baseFolder = os.path.dirname(__file__)
	addons.load("modules")
	addons.load("plugins")
	# Instantiate the main application
	application = app.Application(URLMappings, debug=False, addons=addons)
	return application



def run(application):
	'''
	Run the application with the google webap utility
	'''
	from google.appengine.ext.webapp import util
	util.run_wsgi_app(application)

main = real_main
#main = firepython_main
#main = profile_html_main
#main = profile_log_main
#main = profile_firepython_main

if __name__ == '__main__':
	main()
