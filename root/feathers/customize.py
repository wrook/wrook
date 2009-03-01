#!python
# coding=UTF-8

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import settings

import cgi, datetime, logging
from google.appengine.api import images, memcache
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from django.utils.translation import gettext as _
from feathers import membership
from feathers import utils
import app

def URLMappings():
	return [
		('/Themes', ViewThemes),
		('/Themes/Select', ThemeSelect),
		(r'/Themes/Theme/Edit/(.*)', ThemeEditWithImageUpload),
		( '/Themes/Upload', ThemeUploadNew),
		(r'/Themes/Theme/BackgroundImage/(.*)', ThemeBackgroundImage),
		(r'/Themes/Theme/BackgroundImageInfo/(.*)', ThemeBackgroundImageInfo),
		(r'/Themes/Theme/Stylesheet/(.*)', ThemeStylesheet),
		(r'/Themes/(.*)/MemberSelect', ThemeMemberSelect),
		(r'/Themes/(.*)/BookSelect', ThemeBookSelect),
		(r'/Themes/(.*)', ThemeView)
	]

	def __unicode__(self):
		return self.Title

	def GetStyle(self):
		return None;


class Theme(db.Model):
	Title = db.StringProperty(verbose_name="Title", default=_("New theme"))
	Description = db.TextProperty(verbose_name=_("Description"))
	Created = db.DateTimeProperty(auto_now_add=True, verbose_name=_("Created"))
	isDefault = db.BooleanProperty(default=False, verbose_name=_("Default theme"))
	isTiledImage = db.BooleanProperty(default=None, verbose_name=_("Is a tiled images"))
	SubmitedBy = db.ReferenceProperty(membership.Member, collection_name="SubmitedThemes", verbose_name=_("Submitd by"))
	BackgroundImage = db.BlobProperty(verbose_name=("Background image"))
	BackgroundColor = db.StringProperty(default="#000000", verbose_name=_("Background color"))
	StyleSource = db.TextProperty(verbose_name=_("Style source code"), default="")
	isSharedWithEveryone = db.BooleanProperty(default=True, verbose_name=_("Share with everyone"))

	def selectForMember(self, member):
		if member:
			selection = ThemeMemberSelection(Member=member, Theme=self)
			member.flushCache()
			selection.put()
			return selection
		else: return None

	def __unicode__(self):
		return self.Title

	def GetStyle(self):
		return None;

	def getBackgroundImage(self):
		if self.BackgroundImage:
			image = images.Image(self.BackgroundImage)
			if image: return image
		return None

	def isTiled(self):
		if self.isTiledImage==None:
			image = self.getBackgroundImage()
			if image:
				if (image.width<600 or image.height<600):
					self.isTiledImage = True
				else: self.isTiledImage = False
		return self.isTiledImage


class Moment(db.Model):
	'''
	A moment according to the system.
	
	Moments define periodes of the year where specific customization of the site occurs
	These moments can change de default, the palette, special messages to the user
	'''
	Title = db.StringProperty()
	Begins = db.DateTimeProperty()
	Ends = db.DateTimeProperty()
	Created = db.DateTimeProperty(auto_now_add=True)
	isDefault = db.BooleanProperty(default=False)
	Priority = db.IntegerProperty(required=True, default=0)
		
class ThemeMemberSelection(db.Model):
	WhenSelected = db.DateTimeProperty(auto_now_add=True, verbose_name=_("When selected"))
	Member = db.ReferenceProperty(membership.Member, collection_name="ThemeSelections", verbose_name=_("Member"))
	Theme = db.ReferenceProperty(Theme, collection_name="MemberSelections", verbose_name=_("Theme"))

class ThemeSimpleForm(djangoforms.ModelForm):
	class Meta:
		model = Theme
		fields = ('Title', 'Description', "isSharedWithEveryone", "BackgroundColor")

class ThemeMemberSelect(app.RequestHandler):
	def get(self, key):
		self.onRequest()
		if self.CurrentMember:
			if key:
				theme = Theme.get(key)
				if theme:
					currentThemeSelection = self.CurrentMember.currentThemeSelection()
					if currentThemeSelection:
						if (theme.key() != currentThemeSelection.key()):
							theme.selectForMember(self.CurrentMember)
					else:
						theme.selectForMember(self.CurrentMember)
					self.redirect("/")
				else: self.error(500)
			else: self.error(404)
		else: self.requestLogin()

class ThemeBookSelect(app.RequestHandler):
	def get(self, themeKey, ):
		self.onRequest()
		if self.CurrentMember:
			if key:
				theme = Theme.get(key)
				if theme:
					currentThemeSelection = self.CurrentMember.currentThemeSelection()
					if currentThemeSelection:
						if (theme.key() != currentThemeSelection.key()):
							theme.selectForMember(self.CurrentMember)
					else:
						theme.selectForMember(self.CurrentMember)
					self.redirect("/")
				else: self.error(500)
			else: self.error(404)
		else: self.requestLogin()

class ThemeView(app.RequestHandler):
	def get(self, key):
		self.onRequest()
		if self.CurrentMember:
			if key:
				theme = Theme.get(key)
				if theme:
					self.setCurrentTheme(theme)
					canEditTheme = self.CurrentMember.isAdmin or (self.CurrentMember.key() == theme.SubmitedBy.key())
					self.Model.update({
						'canEditTheme': canEditTheme,
						'theme': theme
						})
					self.TemplateBaseFolder = os.path.dirname(__file__)
					self.render2('views/customize-viewTheme.html')
				else: self.error(500)
			else: self.error(404)
		else: self.requestLogin()

class ThemeEdit(app.RequestHandler):
	def get(self, key):
		self.onRequest()
		if self.CurrentMember:
			if key == "": theme = Theme(SubmitedBy = self.CurrentMember)
			else: theme = Theme.get(key) 
			form = ThemeForm(instance=theme)
			self.Model.update({
				'form': form,
				'theme': theme
				})
			self.TemplateBaseFolder = os.path.dirname(__file__)
			self.render2('views/customize-themeEdit.html')

	def post(self, key):
		self.onRequest()
		if self.CurrentMember:
			if key == "": theme = Theme(SubmitedBy = self.CurrentMember)
			else: theme = Theme.get(key) 
			if self.request.get("doDelete"):
				theme.delete()
				self.redirect('/Themes')
				return
			form = ThemeForm(data=self.request.POST, instance=theme)
			if form.is_valid():
				# Save the form, and redirect to the view page
				entity = form.save(commit=False)
				entity.put()
				self.redirect('/Themes')
			else:
				self.Model.update({
					'theme': theme,
					'form': form
					})
				self.TemplateBaseFolder = os.path.dirname(__file__)
				self.render2("views/customize-themeEdit.html")

class ThemeEditWithImageUpload(app.RequestHandler):
	def get(self, key):
		self.onRequest()
		if self.CurrentMember:
			if key == "": theme = Theme(SubmitedBy = self.CurrentMember)
			else: theme = Theme.get(key) 
			form = ThemeSimpleForm(instance=theme)
			self.Model.update({
				'form': form,
				'theme': theme
				})
			self.TemplateBaseFolder = os.path.dirname(__file__)
			self.render2('views/customize-themeEdit.html')

	def post(self, key):
		self.onRequest()
		if self.CurrentMember:
			if key == "": theme = Theme(SubmitedBy = self.CurrentMember)
			else: theme = Theme.get(key) 
			if self.request.get("doDelete"):
				theme.delete()
				self.redirect('/Themes')
				return
			form = ThemeSimpleForm(data=self.request.POST, instance=theme)
			if form.is_valid():
				imageData = self.request.get('backgroundImageProxy')
				# Save the form, and redirect to the view page
				entity = form.save(commit=False)
				if imageData:
					entity.BackgroundImage = db.Blob(imageData)
				entity.put()
				self.redirect('/Themes')
			else:
				self.Model.update({
					'theme': theme,
					'form': form
					})
				self.TemplateBaseFolder = os.path.dirname(__file__)
				self.render2("views/customize-themeEdit.html")


class ThemeUploadNew(app.RequestHandler):
	def post(self):
		from django.utils import simplejson
		self.onRequest()
		if self.CurrentMember:
			imageData = self.request.get('photoupload')
			if imageData:
				image = images.Image(imageData)
				if image:
					theme = Theme()
					theme.BackgroundImage = db.Blob(imageData)
					theme.SubmitedBy = self.CurrentMember
					theme.isSharedWithEveryone = True
					theme.put()
					result = {"result":"success", "size":_("Image received (%s x %s)!") % (image.width, image.height)}
				else:
					result = {"result":"failed", "error":_("This file was not a recognized image")}
			else:
				result = {"result":"failed", "error":_("No file data was received")}
		else:
			result = {"result":"failed", "error":_("You must be logged-in to upload an image.(%s)" % self.debug)}
		self.response.out.write("%s" % simplejson.dumps(result))


class ThemeBackgroundImageInfo(app.RequestHandler):
	def get(self, key):
		import getimageinfo
		theme = db.get(key)
#		image = images.Image(theme.BackgroundImage)
		info = getimageinfo.getImageInfo(theme.BackgroundImage)
		self.response.out.write("info : %s, %s, %s" % info)
"""
import png

point = (10, 20) # coordinates of pixel to read

reader = png.Reader(filename='image.png') # streams are also accepted
w, h, pixels, metadata = reader.read()
pixel_byte_width = 4 if metadata['has_alpha'] else 3
pixel_position = point[0] + point[1] * w
print pixels[
  pixel_position * pixel_byte_width :
  (pixel_position + 1) * pixel_byte_width]

"""

class ThemeBackgroundImage(app.RequestHandler):
	def get(self, key):
		theme = db.get(key)
		if theme:
			paramWidth = self.request.get("width")
			mode = "fitWidth"
			if paramWidth == "80x80":
				mode = "fitToBoth"
				width = 80
				height = 80
			elif paramWidth == "120x120":
				mode = "fitToBoth"
				width = 120
				height = 120
			elif paramWidth == "160x160":
				mode = "fitToBoth"
				width = 160
				height = 160
			elif paramWidth == "120":
				width = 120
				height = 90
			elif paramWidth == "240":
				width = 240
				height = 180
			elif paramWidth == "1024":
				width = 1024
				height = 768
			elif paramWidth == "980":
				width = 980
				height =835
			else:
				width = 0
				height = 0
			imageKey = "themeThumb-%s-%s" % (paramWidth, theme.key())
			thumbnailData = memcache.get(imageKey)
			if thumbnailData is None:
				crop0 = 0
				crop90 = 1
				crop180 = 1
				crop270 = 0
				if width > 0:
					image = images.Image(theme.BackgroundImage)
					if mode == "fitToBoth":
						currentRatio = float(image.width) / float(image.height)
						newRatio = width / height
						diffRatio = currentRatio / newRatio
						if diffRatio > 1:
							cropOffset = (1-(newRatio / currentRatio)) / 2
							width = width * diffRatio
							crop0 = 0
							crop90 = 1 - cropOffset
							crop180 = 1
							crop270 = cropOffset
						else:
							cropOffset = (1-(currentRatio / newRatio)) / 2
							crop0 = cropOffset
							crop90 = 1
							crop180 = 1 - cropOffset
							crop270 = 0
							height = height / diffRatio

					image.resize(int(width), int(height))
					image.crop(float(crop270), float(crop0), float(crop90), float(crop180))
					thumbnailData = image.execute_transforms(output_encoding=images.JPEG)
				else:
					thumbnailData = theme.BackgroundImage
				memcache.add(imageKey, thumbnailData)

			self.response.headers['content-type'] = "image/png"
			self.response.headers['cache-control'] = "public, max-age=1814400" # 21 day cache
			self.response.headers["Expires"] = "Thu, 01 Dec 2014 16"
			self.response.out.write(thumbnailData)
		else:
			self.error(404)

class ViewThemes(app.RequestHandler):
	def get(self):
		self.onRequest()
		if self.CurrentMember:
			self.Model.update({
				"themes": Theme.all()
				})
			self.TemplateBaseFolder = os.path.dirname(__file__)
			self.render2("views/customize-viewThemes.html")

class ThemeSelect(app.RequestHandler):
	def get(self):
		self.onRequest()
		if self.CurrentMember:
			self.Model.update({
				"themes": Theme.all(),
				"themeUsage": self.request.get("themeUsage"),
				"redirect": self.request.get("redirect")
				})
			self.TemplateBaseFolder = os.path.dirname(__file__)
			self.render("views/customize-selectTheme.html")

class ThemeStylesheet(app.RequestHandler):
	def get(self, key):
		self.onRequest()
		theme = Theme.get(key)
		self.Model.update(utils.styleSourceToDict(theme.StyleSource))
		self.response.headers["Content-Type"] = "text/css"
		self.response.headers['cache-control'] = "public, max-age=75600" #21 day cache
		self.response.headers["Expires"] = "Thu, 01 Dec 2014 16"
		self.TemplateBase = os.path.dirname(__file__)
		self.render('views/customize-theme-stylesheet.css')


