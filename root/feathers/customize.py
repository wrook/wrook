import os, cgi, datetime, logging
from google.appengine.api import images, memcache
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from django.utils.translation import gettext as _
from feathers import membership, utils, webapp


def URLMappings():
	return [
		('/Themes', ViewThemes),
		('/Themes/Select', ThemeSelect),
		(r'/Themes/Theme/Edit/(.*)', ThemeEditWithImageUpload),
		(r'/Themes/Theme/BackgroundImage/(.*)', ThemeBackgroundImage),
		(r'/Themes/Theme/Stylesheet/(.*)', ThemeStylesheet),
		(r'/Themes/(.*)/MemberSelect', ThemeMemberSelect),
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
	SubmitedBy = db.ReferenceProperty(membership.Member, collection_name="SubmitedThemes", verbose_name=_("Submitd by"))
	BackgroundImage = db.BlobProperty(verbose_name=("Background image"))
	BackgroundColor = db.StringProperty(default="#000000", verbose_name=_("Background color"))
	StyleSource = db.TextProperty(verbose_name=_("Style source code"), default="")
	isSharedWithEveryone = db.BooleanProperty(default=True, verbose_name=_("Share with everyone"))
	#Refactor: Still needed ?
	# StyleSource = db.TextProperty(verbose_name="Style source code", default=
# """
# headerBannerImageURL: ;
# headerBannerRepeatImageURL: ;
# WallpaperImageURL: ;
# """)

	def selectForMember(self, member):
		if member:
			selection = ThemeMemberSelection(Member=member, Theme=self)
			selection.put()
			return selection
		else: return None

	def __unicode__(self):
		return self.Title

	def GetStyle(self):
		return None;

def onRequest(request): # Event triggering to let the host application intervene
	pass

class ThemeMemberSelection(db.Model):
	WhenSelected = db.DateTimeProperty(auto_now_add=True, verbose_name=_("When selected"))
	Member = db.ReferenceProperty(membership.Member, collection_name="ThemeSelections", verbose_name=_("Member"))
	Theme = db.ReferenceProperty(Theme, collection_name="MemberSelections", verbose_name=_("Theme"))

class ThemeSimpleForm(djangoforms.ModelForm):
	class Meta:
		model = Theme
		fields = ('Title', 'Description', "isSharedWithEveryone", "BackgroundColor")

class ThemeMemberSelect(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
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


class ThemeView(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
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
					self.TemplateBase = os.path.dirname(__file__)
					self.render('views/customize-viewTheme.html')
				else: self.error(500)
			else: self.error(404)
		else: self.requestLogin()

class ThemeEdit(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			if key == "": theme = Theme(SubmitedBy = self.CurrentMember)
			else: theme = Theme.get(key) 
			form = ThemeForm(instance=theme)
			self.Model.update({
				'form': form,
				'theme': theme
				})
			self.TemplateBase = os.path.dirname(__file__)
			self.render('views/customize-themeEdit.html')

	def post(self, key):
		onRequest(self)
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
				self.TemplateBase = os.path.dirname(__file__)
				self.render("views/customize-themeEdit.html")

class ThemeEditWithImageUpload(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			if key == "": theme = Theme(SubmitedBy = self.CurrentMember)
			else: theme = Theme.get(key) 
			form = ThemeSimpleForm(instance=theme)
			self.Model.update({
				'form': form,
				'theme': theme
				})
			self.TemplateBase = os.path.dirname(__file__)
			self.render('views/customize-themeEdit.html')

	def post(self, key):
		onRequest(self)
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
				self.TemplateBase = os.path.dirname(__file__)
				self.render("views/customize-themeEdit.html")

class ThemeBackgroundImage(webapp.RequestHandler):
	def get(self, key):
		theme = db.get(key)
		if theme:
			paramWidth = self.request.get("width")
			if paramWidth == "120":
				width = 120
				height = 90
			elif paramWidth == "240":
				width = 240
				height = 180
			elif paramWidth == "1024":
				width = 1024
				height = 768
			else:
				width = 160
				height = 120
			imageKey = "themeThumb" + str(width) + "-%s" % theme.key()
			thumbnailData = memcache.get(imageKey)
			thumbnailData = None
			if thumbnailData is None:
				image = images.Image(theme.BackgroundImage)
				image.resize(width, 0)
				thumbnailData = image.execute_transforms(output_encoding=images.JPEG)
				memcache.add(imageKey, thumbnailData)

			self.response.headers['content-type'] = "image/png"
			self.response.headers['cache-control'] = "public, max-age=1814400" # 21 day cache
			self.response.headers["Expires"] = "Thu, 01 Dec 2014 16"
			self.response.out.write(thumbnailData)
		else:
			self.error(404)

class ViewThemes(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({
				"themes": Theme.all()
				})
			self.TemplateBase = os.path.dirname(__file__)
			self.render("views/customize-viewThemes.html")

class ThemeSelect(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({
				"themes": Theme.all(),
				"themeUsage": self.request.get("themeUsage"),
				"redirect": self.request.get("redirect")
				})
			self.TemplateBase = os.path.dirname(__file__)
			self.render("views/customize-selectTheme.html")

class ThemeStylesheet(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		theme = Theme.get(key)
		self.Model.update(utils.styleSourceToDict(theme.StyleSource))
		self.response.headers["Content-Type"] = "text/css"
		self.response.headers['cache-control'] = "public, max-age=75600" #21 day cache
		self.response.headers["Expires"] = "Thu, 01 Dec 2014 16"
		self.TemplateBase = os.path.dirname(__file__)
		self.render('views/customize-theme-stylesheet.css')


