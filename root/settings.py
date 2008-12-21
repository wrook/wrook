# DO NOT DELETE! This is needed by Django
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG
LANGUAGE_CODE = "en"
DEFAULT_CHARSET = "utf-8"
PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIRS = (
	os.path.join(PROJECT_PATH, 'views')
	)
TEMPLATE_LOADERS = (
	'django.template.loaders.filesystem.load_template_source',
	'django.template.loaders.app_directories.load_template_source'
	)


