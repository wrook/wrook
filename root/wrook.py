#!python
# coding=UTF-8
'''
Wrook's main module
'''

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings

from firepython.middleware import FirePythonWSGI

#Feathers imports
from feathers import webapp
from feathers import stories
from feathers import utils
from feathers import customize
from feathers import membership
from feathers import labs
from feathers import proforma
from feathers import talk

#Wrook modules
import app
import about
import wrookStories
import admin
import books
import members

#TODO: Figure out what this means and if its necessary
settings._target = None #i18n fix

def integrate_modules(URLMappings):
	#TODO:Figure out a better way of integrating modules
	# Integrate the about module
	URLMappings += about.URLMappings()
	about.onRequest = app.onRequest
	# Integrate the admin module
	URLMappings += admin.URLMappings()
	admin.onRequest = app.onRequest
	# Integrate the admin module
	URLMappings += books.URLMappings()
	books.onRequest = app.onRequest
	# Integrate the Labs module
	URLMappings += stories.URLMappings()
	stories.onRequest = app.onRequest
	# Integrate the Labs module
	URLMappings += labs.URLMappings()
	labs.onRequest = app.onRequest
	# Integrates the Customize module
	URLMappings += customize.URLMappings()
	customize.onRequest = app.onRequest
	# Integrates the Membership module
	URLMappings += membership.URLMappings()
	membership.onRequest = app.onRequest
	# Integrates the Membership module
	URLMappings += proforma.URLMappings()
	proforma.onRequest = app.onRequest
	# Integrate the Talk module
	URLMappings += talk.URLMappings()
	talk.onRequest = app.onRequest
	# Integrate the Talk module
	URLMappings += members.URLMappings()
	members.onRequest = app.onRequest
	return URLMappings

def real_main():
	'''
	The basic main function to start the application
	on the production servers
	'''
	webapp.run(application)

def firepython_main():
	'''
	The basic main function to start the application
	on the production servers
	'''
	webapp.run(FirePythonWSGI(application))

def profile_log_main():
	'''
	Main function used for profiling to the log files.
	'''
	#TODO: Find a way to send the profiler log results to FirePython
	import cProfile
	import logging
	import pstats
	import StringIO
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
	prof = cProfile.Profile()
	prof = prof.runctx("firepython_main()", globals(), locals())
	stream = StringIO.StringIO()
	stats = pstats.Stats(prof, stream=stream)
	stats.sort_stats("cumulative")  # Or cumulative
	stats.print_stats(100)  # 80 = how many to print
	logging.info("pfff!")
	logging.info("Profile data:\n%s", stream.getvalue())


application = webapp.Application(
	integrate_modules([]),
	debug=True) # Instantiate the main application

#main = real_main
#main = firepython_main
#main = profile_html_main
#main = profile_log_main
main = profile_firepython_main

if __name__ == '__main__':
	main()
