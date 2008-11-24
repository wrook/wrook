'''
Wrook's Test Runner Module.

This module is used to load and patch the necessary modules for
running all the Doctests routines.
'''
import sys, os, StringIO
sys.path = sys.path + [
	'/Python25/Lib/site-packages',
	'/Python25/Lib/site-packages/epydoc',
	'/Program Files/Google/google_appengine',
	'/Program Files/Google/google_appengine/lib/django',
	'/Program Files/Google/google_appengine/lib/webob',
	'/Program Files/Google/google_appengine/lib/yaml/lib',
	'/Program Files/Google/google_appengine/google/appengine',
	'/wrook/root/latest/',
	'/wrook/root/latest/root']

import wrook

def getTestResults():
	import imp
	# doctest uses imp.get_suffixes - but appengine doesn't allow the use of imp.
	# It is only to check module for binary so we can bypass it.
	def get_suffixes(): return None
	imp.get_suffixes = get_suffixes

	import sys
	import doctest
	import doctest_runner
	stdout = sys.stdout
	sys.stdout = StringIO.StringIO()
	doctest.testmod(wrook, verbose=False)
	content = sys.stdout.getvalue()
	sys.stdout = stdout
	return ("<pre class='py-doctest'>" + content + "</pre>")
