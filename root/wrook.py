#!python
# coding: utf-8
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import sys, cgi, datetime, logging, urllib, hashlib, types

import diff, markdown2
from string import Template
from google.appengine.api import urlfetch, users, mail, images, memcache
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

from django.utils import translation
from django.utils.translation import gettext as _
from django.conf import settings
from django.db import models
#from django import newforms as forms 
from django import forms 

from feathers import webapp, stories, utils, customize, membership, labs, proforma, talk

import licensing

#-------------------- i18n FIX start --------------------
settings._target = None
#-------------------- i18n FIX end --------------------


class WrookRequestHandler(webapp.RequestHandler):
	pass

def onRequest(self):
	self.Model = {}
	self.MasterTemplate = os.path.join(os.path.dirname(__file__), "views/template-main-d.html") # Sets the default template to be used by hosted modules
	self.CurrentMember = membership.loginFromCookies(self) # Load the current member from the google authentication and add it to the requesthandler
	self.CurrentTheme = getDefaultTheme() # Set the default theme as the current theme
	self.AppConfig = getWrookAppConfig() # Load the application config from the database
	if self.CurrentMember: translation.activate(self.CurrentMember.PreferedLanguage) # If the is a current member, his prefered language is activated
	else: translation.activate("en") # If not, the default language is set to english
	self.Model.update({
		'now': datetime.datetime.now(), # Add the current time tot the model
		'currentMember': self.CurrentMember, # Add the current user to the model
		'currentTheme': self.CurrentTheme, # Add the default theme to the model
		'appConfig': self.AppConfig # Add the app config to the model
		})

# Moments define periodes of the year where specific customization of the site occurs
# These moments can change de default, the palette, special mssages to the user
class Moment(db.Model):
	Title = db.StringProperty()
	Begins = db.DateTimeProperty()
	Ends = db.DateTimeProperty()
	Created = db.DateTimeProperty(auto_now_add=True)
	Theme = db.ReferenceProperty(customize.Theme, collection_name=_("Moments"))
	isDefault = db.BooleanProperty(default=False)
	Priority = db.IntegerProperty(required=True, default=0)

class Cover(db.Model):
	SampleTitle = db.StringProperty()
	TitleColor = db.StringProperty()
	ThumbnailImage = db.BlobProperty(verbose_name=_("Image"))
	Created = db.DateTimeProperty(auto_now_add=True)
	CreatedBy = db.ReferenceProperty(membership.Member, collection_name="Covers", verbose_name=_("Created by"))
	isReusable = db.BooleanProperty(default=False, verbose_name=_("Is this cover reusable for other books?"))
	isSharedWithEveryone = db.BooleanProperty(default=False, verbose_name=_("Share with everyone"))

	def thumbURL(self):
		if self.is_saved():
			return "/Covers/Thumbnail/%s?width=120" % self.key()

	def thumbURL45(self):
		if self.is_saved():
			return "/Covers/Thumbnail/%s?width=45" % self.key()

	def imageURL(self):
		if self.is_saved():
			return "http://www.wrook.org/Covers/Image/%s" % self.key()

class Book(db.Model):
	Title = db.StringProperty(default=_("New book..."), required=True, verbose_name=_("Title"))
	Author = db.ReferenceProperty(membership.Member, collection_name="Books", verbose_name=_("Author"))
	Slug = db.StringProperty(verbose_name=_("Slug"))
	Stage = db.StringProperty(required=True, default="planning", verbose_name=_("Stage"), choices=set(["planning", "drafting", "writing", "proofing", "final"]))
	Cover = db.ReferenceProperty(Cover, collection_name="Books", verbose_name=_("Cover"))
	Synopsis = db.TextProperty(verbose_name=_("Synopsis"))
	NoteFromAuthor = db.TextProperty(verbose_name=_("Note from the author"))
	License = db.ReferenceProperty(licensing.LicenseType, collection_name="Books", verbose_name=_("License"))
	AttribDetailed = db.TextProperty(verbose_name=_("Attribution"))
	AttribAuthorIsAuthor = db.BooleanProperty(default=True, verbose_name=_("Are you the author"))
	AttribAuthorName = db.StringProperty(verbose_name=_("Author's name"))
	

	def clearCache(self):
		memcache.delete("wordcount-%s" % self.key) # Removes the wordCount cache

	# Does a word count of all chapters, any chapter missings its word count will do it on the fly
	# Cache results for an undeterminate time
	def wordCount(self):
		wordCountKey = "wordcount-%s" % self.key
		wordCount = memcache.get(wordCountKey)
		if not wordCount:
			wordCount = 0
			for chapter in self.Chapters:
				wordCount += chapter.getLatestRevision().calculateWordCount()
			memcache.add(wordCountKey, wordCount)
		return wordCount

	def authorName(self):
		if self.AttribAuthorIsAuthor: return self.Author.fullname()
		elif self.AttribAuthorName: return self.AttribAuthorName
		else: return _("Mr. Unknown")

	def getCover(self):
		if self.Cover: return self.Cover
		else:
			appConfig = getWrookAppConfig()
			if appConfig: return appConfig.DefaultCover
		return None

	def firstChapter(self):
		chapter = Chapter.all().filter("Book =", self).fetch(limit=1)
		if len(chapter) > 0:
			return chapter[0]

	def lastRevisedChapter(self):
		revision = Revision.all().filter("Book =", self).order("-Created").fetch(limit=1)
		if len(revision) > 0:
			return revision[0].Chapter

	def countReaders(self):
		return len(Bookmark().all().filter("Book =", self).fetch(limit=999))

	def markdownAttribDetailed(self):
		return markdown2.markdown(self.AttribDetailed)

class BookForm(djangoforms.ModelForm):
	class Meta:
		model = Book
		fields = ('Title', 'Stage', "Slug", 'Synopsis', 'NoteFromAuthor')

class BookLicenseForm(djangoforms.ModelForm):
	class Meta:
		model = Book
		fields = ('License', 'AttribDetailed', 'AttribAuthorIsAuthor', 'AttribAuthorName')

class Chapter(db.Model):
	Book = db.ReferenceProperty(Book, collection_name="Chapters")
	Number = db.IntegerProperty(default=0)
	Name = db.StringProperty(default=_("Chapter X"), required=True)
	Title = db.StringProperty(default="")
	Stage = db.StringProperty(required=True, default="planning", choices=set(["planning", "drafting", "writing", "proofing", "final"]))
	Synopsis = db.TextProperty()
	Created = db.DateTimeProperty(auto_now_add=True)
	isDeleted = db.BooleanProperty(default = False) # An author can mark a chapter as being deleted without loosing the revision history

	def addRevision(self, text):
		LatestRevisionVersion = 0
		latestRevision = self.getLatestRevision()
		if latestRevision:
			LatestRevisionVersion = latestRevision.Version
		revision = Revision(
			Book = self.Book,
			Chapter = self,
			Version = LatestRevisionVersion + 1,
			Text = text
			)
		revision.put()
		self.put()
	
	def getLatestRevision(self):
		latest = self.Revisions.order("-Created").fetch(limit=1)
		if len(latest) == 0:
			return None
		else:
			return latest[0]

	def getLatestPublishedRevision(self):
		latest = self.Revisions.filter("isPublished", True).order("-Created").fetch(limit=1)
		if len(latest) == 0:
			return None
		else:
			return latest[0]

	def setBookmark(self, member):
		chapter = self
		bookmarks = Bookmark.all().filter("Reader =", member).filter("Book =", chapter.Book).fetch(limit=999)
		# If this is a first read, a story is posted
		if len(bookmarks) == 0: 
			story = StoryMemberStartReadingBook()
			occurence = story.createOccurence({
				"member": member,
				"book": self.Book
				})
			occurence.publish()

		db.delete(bookmarks)
		bookmark = Bookmark(
			Chapter = chapter,
			Book = chapter.Book,
			Author = chapter.Book.Author,
			Reader = member
		)
		bookmark.put()
		member.isReader = True
		member.put()
		return chapter

	def nextChapter(self):
		#chapters = self.Book.Chapters()
		chapters = Chapter.all().filter("Book =", self.Book).fetch(limit=999)
		i = 0
		for chapter in chapters:
			if chapter.key() == self.key():
				if i+1 < len(chapters):
					return chapters[i+1]
			i=i+1

	def previousChapter(self):
		#chapters = self.Book.Chapters()
		chapters = Chapter.all().filter("Book =", self.Book).fetch(limit=999)
		i = 0
		for chapter in chapters:
			if chapter.key() == self.key():
				if i > 0:
					return chapters[i-1]
			i=i+1

class ChapterForm(djangoforms.ModelForm):
	class Meta:
		model = Chapter
		fields = ("Name", "Title", "Stage", "Synopsis")

class ChapterFormForCreate(djangoforms.ModelForm):
	class Meta:
		model = Chapter
		fields = ("Name", "Title", "Stage")

class Revision(db.Model):
	Book = db.ReferenceProperty(Book, collection_name="ChapterRevisions")
	Chapter = db.ReferenceProperty(Chapter, collection_name="Revisions")
	Version = db.IntegerProperty()
	WordCount = db.IntegerProperty(default=0)
	Text = db.TextProperty()
	NoteFromAuthor = db.TextProperty()
	Created =  db.DateTimeProperty(auto_now_add=True)
	isPublished = db.BooleanProperty(default = True)

	def calculateWordCount(self):
		if self.WordCount: return self.WordCount
		else:
			self.WordCount = utils.wordCount(self.Text)
			return self.WordCount

	def markdownText(self):
		return markdown2.markdown(self.Text)

	def diffFromLatest(self):
		latest = self.Chapter.getLatestRevision()
		if latest.key != self.key:
			return diff.textDiff(latest.Text, self.Text)
		else:
			return self.Text
			
	def diffFromPrevious(self):
		if self.Version > 1:
			previousRevision = Revision.all().filter("Chapter =", self.Chapter).filter("Version =", self.Version-1).fetch(limit=1)[0] 
			return diff.textDiff(previousRevision.Text, self.Text)
		else:
			return self.Text

class Bookmark(db.Model):
	Chapter = db.ReferenceProperty(Chapter, collection_name="Bookmarks")
	Book = db.ReferenceProperty(Book, collection_name="Bookmarks")
	Author = db.ReferenceProperty(membership.Member, collection_name="ReaderBookmarks")
	Reader = db.ReferenceProperty(membership.Member, collection_name="Bookmarks")
	When = db.DateTimeProperty(auto_now_add=True)

#TODO: Refactor -  Replace with the Talk module
class Message(db.Model):
	Chapter = db.ReferenceProperty(Chapter, collection_name="Feedback")
	Book = db.ReferenceProperty(Book, collection_name="Feedback")
	Author = db.ReferenceProperty(membership.Member, collection_name="FeedbackReceived", required=True)
	From = db.ReferenceProperty(membership.Member, collection_name="FeedbackGiven", required=True)
	Topic = db.StringProperty()
	Text = db.TextProperty(required=True)
	Sent = db.DateTimeProperty(auto_now_add=True)
	ReplyTo = db.SelfReferenceProperty(collection_name="Replies")
	isPrivate = db.BooleanProperty(default = False) # Only the author of the book will see this message
	isForcedPrivate = db.BooleanProperty(default = False) # The author has forced this message to be private
	targetType = db.StringProperty(required=True, choices=set(["chapter", "book", "author"]))

	def forcePrivate(self):
		self.isPrivate = True
		self.isForcedPrivate = True

class CoverForm(djangoforms.ModelForm):
	class Meta:
		model = Cover
		fields = ("SampleTitle", "TitleColor", "isReusable")

#TODO: Refactor -  should be secure for admins???
class CoverSetDefault(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			key = self.request.get("selected")
			if key:
				cover = Cover.get(key)
				if cover:
					if not self.AppConfig: self.AppConfig = WrookAppConfig()
					self.AppConfig.DefaultCover = cover
					self.AppConfig.put()
					page = proforma.SuccessPage()
					page.Model={
						"Statement": _("The default cover has been set!"),
						"ContinueURL": "/Covers/",
						"ContinueLabel": _("Back to the covers")}
					self.redirect(page.url())
				else: self.error(404)
			else: self.error(500)
		else: self.requestLogin()

class BookSetCover(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key)
			selected = self.request.get("selected")
			if selected and book:
				cover = Cover.get(selected)
				if cover:
					book.Cover = cover
					book.put()
					page = proforma.SuccessPage()
					page.Model={
						"Statement": _("The cover has been changed!"),
						"ContinueURL": "/Books/" + key,
						"ContinueLabel": _("Back to the book")}
					self.redirect(page.url())
				else: self.error(404)
			else: self.error(500)
		else: self.requestLogin()

class CoverEdit(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			if key: cover = Cover.get(key)
			else: cover = Cover()
			form = CoverForm(instance=cover)
			self.Model.update({
				'form': form
				})
			self.render('views/covers-edit.html')
		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			if key: cover = Cover.get(key)
			else: cover = Cover(CreatedBy=self.CurrentMember)
			if self.request.get("doDelete"):
				if cover.Books:
					#TODO: Refactor -  Replace this with the proforma module
					self.response.out.write(_("This cover is already in use by other book. It was not deleted"))
				else:
					db.delete(cover)
					self.redirect("/Covers/")
				return
			form = CoverForm(self.request.POST, instance=cover)
			if form.is_valid():
				# Save the form, and redirect to the view page
				entity = form.save(commit=False)
				thumbnailImageProxy = self.request.get('thumbnailImageProxy')
				if thumbnailImageProxy: entity.ThumbnailImage = db.Blob(thumbnailImageProxy)
				entity.put()
				self.redirect('/Covers/')
			else:
				self.Model.update({'form': form})
				self.render("views/cover-edit.html")
		else: self.requestLogin()

class CoverThumbnail(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if key: cover = db.get(key)
		elif self.AppConfig: cover = self.AppConfig.DefaultCover
		else: cover = None
		paramWidth = self.request.get("width")
		if paramWidth == "45":
			width = 45
			height = 60
		elif paramWidth == "90":
			width = 90
			height = 120
		elif paramWidth == "180":
			width = 180
			height = 240
		else:
			width = 120
			height = 160
		if cover:
			imageKey = "coverThumb%s-%s" % (width, cover.key())
			thumbnailData = memcache.get(imageKey)
			if thumbnailData is None:
				image = images.Image(cover.ThumbnailImage)
				image.resize(width, height)
				thumbnailData = image.execute_transforms(output_encoding=images.PNG)
				memcache.add(imageKey, thumbnailData)
			self.response.headers['content-type'] = "image/jpg"
			self.response.headers['cache-control'] = "public, max-age=1814400" # 21 day cache
			self.response.headers["Expires"] = "Thu, 01 Dec 2014 16"
			self.response.out.write(thumbnailData)
		else: self.error(404)

class CoverImage(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		cover = Cover.get(key)
		if cover:
			image = images.Image(cover.ThumbnailImage)
			image.rotate(0)
			thumbnailData = image.execute_transforms(output_encoding=images.PNG)

			self.response.headers['content-type'] = "image/png"
			self.response.headers['cache-control'] = "public, max-age=600" # 10 minute cache
			self.response.headers["Expires"] = "Thu, 01 Dec 2014 16"
			self.response.out.write(thumbnailData)
		else:
			self.error(404)

	def post(self, key):
		onRequest(self)
		cover = Cover.get(key)
		if cover:
			cover.ThumbnailImage = db.Blob(self.request.get('imageData'))
			cover.put()
			memcache.delete("coverImage-%s" % cover.key())
			memcache.delete("coverThumb45-%s" % cover.key())
			memcache.delete("coverThumb90-%s" % cover.key())
			memcache.delete("coverThumb120-%s" % cover.key())
			memcache.delete("coverThumb180-%s" % cover.key())
			self.response.out.write("Done!")
		else:
			self.error(404)
		
	

class CoverList(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({
				'yourPrivateCovers': Cover.all().filter("CreatedBy =", self.CurrentMember).filter("isSharedWithEveryone =", False),
				'yourSharedCovers': Cover.all().filter("CreatedBy =", self.CurrentMember).filter("isSharedWithEveryone =", True),
				'allSharedCovers': Cover.all().filter("isSharedWithEveryone =", True)
				})
			self.render('views/covers-list.html')
		else: self.requestLogin()

class CoverSelect(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({
				'usage': self.request.get("usage"),
				'redirect': self.request.get("redirect"),
				'yourPrivateCovers': Cover.all().filter("CreatedBy =", self.CurrentMember).filter("isSharedWithEveryone =", False),
				'yourSharedCovers': Cover.all().filter("CreatedBy =", self.CurrentMember).filter("isSharedWithEveryone =", True),
				'allSharedCovers': Cover.all().filter("isSharedWithEveryone =", True)
				})
			self.render('views/covers-select.html')
		else: self.requestLogin()

class CoverView(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			cover = Cover.get(key)
			if cover:
				self.Model.update({
					'cover': cover,
					'picnikKey': picnikKey
					})
				self.render('views/covers-view.html')
			else: self.error(404)
		else: self.requestLogin()

class CoverShare(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			cover = db.get(key)
			if cover:
				cover.isSharedWithEveryone = True
				cover.put()
				self.redirect('/Covers/%s' % cover.key())
			else: self.error(404)
		else: self.requestLogin()

class CoverUnshare(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			cover = db.get(key)
			if cover:
				cover.isSharedWithEveryone = False
				cover.put()
				self.redirect('/Covers/%s' % cover.key())
			else: self.error(404)
		else: self.requestLogin()

class Customize(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({
				"latestCovers": Cover.all().fetch(limit=3),
				"latestThemes": customize.Theme.all().fetch(limit=3)
				})
			self.render("views/customize.html")

class Login(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({
				'error': _("You are already logged in. In order to login again, you must first logout.")
				})
			self.render('views/login-already.html')
		else:
			username = self.request.get("username")
			password = self.request.get("password")
			self.Model.update({
				'username': username,
				'password': password
				})
			self.render('views/login.html')

	def post(self):
		onRequest(self)
		username = self.request.get("username")
		password = self.request.get("password")
		error = None
		if username and password:
			result = membership.memberLogin(self, username, password)
			if not result.ErrorCode:
				self.redirect("/")
				return
			else:
				error = _("<strong>Login failed:</strong> ") + result.ErrorMessage
		else:
			error = _("<strong>Login failed:</strong> Username and password are both mandatory!")

		self.Model.update({
			'error': error,
			'username': username,
			'password': password
			})
		self.render('views/login.html')
		

class Logout(WrookRequestHandler):
	def get(self):
		membership.logout(self)
		self.redirect("/")

class Join(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			self.redirect("/") # Refactor: This special case should be handled: "Accept invite while being already logged in"
		else:
			if key: invite = membership.Invite.get(key)
			else: invite = membership.Invite()
			self.Model.update({
				"invite": invite,
				"email": invite.Email.strip().lower(),
				"firstname": invite.Firstname.strip(),
				"lastname": invite.Lastname.strip()
				})
			self.render('views/join.html')

	def post(self, key): #TODO: Refactor -  This handler should be moved to the membership module and actuel business logic should be in separate methods
		onRequest(self)
		if key: invite = membership.Invite.get(key)
		else: invite = membership.Invite()
		username = self.request.get("Username").strip().lower() #TODO: Stripping and lowercasing should also be in the class logic
		email = self.request.get("Email").strip().lower() #TODO: Stripping and lowercasing should also be in the class logic
		firstname = self.request.get("Firstname").strip()
		lastname = self.request.get("Lastname").strip()
		gender = self.request.get("Gender")
		preferedLanguage = self.request.get("PreferedLanguage")
		isValid = True
		if (firstname == "" or lastname == "" or email == "" or username == ""):
			isValid = False
			error = _("Username, email, firstname and lastname are madatory!")
		elif (not username.isalnum()):
			isValid = False
			error = _("Sorry, the username can only contain letters and numbers.")
		elif (membership.getMemberFromCredentials(email)): #TODO: Refactor -  This constraint should be built into the Member entity
			isValid = False
			error = _("This email address is already used by another member")
		elif (membership.getMemberFromCredentials(username)): #TODO: Refactor -  This constraint should be built into the Member entity
			isValid = False
			error = _("This username address is already used by another member")
		if (not isValid):
			self.Model.update({
				'username': username,
				'email': email,
				'firstname': firstname,
				'lastname': lastname,
				'gender': gender,
				'preferedLanguage': preferedLanguage,
				'error': error
				})
			self.render("views/join.html")
		else:
			member = membership.Member(
				Username = username,
				Email = email,
				Firstname = firstname,
				Lastname = lastname,
				Gender = gender,
				PreferedLanguage = preferedLanguage,
				)
			member.put()
			member.resetPassword(self.AppConfig.EncryptionKey)
			if invite:
				invite.AcceptedMember = member
				invite.Status = "accepted"
				invite.WhenAccepted = datetime.datetime.now()
				invite.put()
			self.redirect("/ResetPassword/%s" % member.key())


class AccountView(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			self.Model.update({
				'member': self.CurrentMember
				})
			self.render('views/viewAccount.html')
		else: self.requestLogin()

class EditAccount(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			if self.CurrentMember.ProfilePhoto: hasProfilePhoto = True
			else: hasProfilePhoto = False
			self.Model.update({
				'key': self.CurrentMember.key(),
				'firstname': self.CurrentMember.Firstname,
				'lastname': self.CurrentMember.Lastname,
				'hasProfilePhoto': hasProfilePhoto,
				'gender': self.CurrentMember.Gender,
				'preferedLanguage': self.CurrentMember.PreferedLanguage,
				'about': self.CurrentMember.About
				})
			self.render('views/editAccount.html')
		else: self.requestLogin()

	def post(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			firstname = self.request.get("Firstname")
			lastname = self.request.get("Lastname")
			preferedLanguage = self.request.get("PreferedLanguage")
			gender = self.request.get("Gender")
			about = self.request.get("About")
			tmpProfilePhoto = self.request.get("profilePhotoProxy")
			if tmpProfilePhoto: profilePhoto = db.Blob(tmpProfilePhoto)
			else: profilePhoto = None
			if (firstname == "" or lastname == ""):
				self.Model.update({
					'firstname': firstname,
					'lastname': lastname,
					'preferedLanguage': preferedLanguage,
					'gender': gender,
					'about': about,
					'error': _("Firstname and lastname are madatory! You will also have to re-upload your photo!") #Refacfor: There should be a way not to forget the photo... temp area?
					})
				self.render('views/editAccount.html')
			else:
				member = self.CurrentMember
				member.Firstname = firstname
				member.Lastname = lastname
				member.PreferedLanguage = preferedLanguage
				member.Gender = gender
				member.About = about
				if profilePhoto: member.ProfilePhoto = profilePhoto
				member.put()
				self.redirect("/Account/View")
		else: self.requestLogin()

class AccountChangeProfilePhoto(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			self.Model.update({
				'member': self.CurrentMember,
				})
			self.render('views/account-changePhoto.html')
		else: self.requestLogin()

	def post(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			tmpProfilePhoto = self.request.get("profilePhotoProxy")
			if tmpProfilePhoto: profilePhoto = db.Blob(tmpProfilePhoto)
			else: profilePhoto = None
			if not profilePhoto:
				self.Model.update({
					'error': _("No file were uploaded!") #Refacfor: There should be a way not to forget the photo... temp area?
					})
				self.render('views/editAccount.html')
			else:
				member = self.CurrentMember
				member.ProfilePhoto = profilePhoto
				member.put()
				member.flushCache()
				self.redirect("/Account/View")
		else: self.requestLogin()


class AccountChangePassword(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			self.render('views/account-changePassword.html')
		else: self.requestLogin()

	def post(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			oldPassword = self.request.get("oldPassword")
			newPassword = self.request.get("newPassword")
			oldEncryptedPassword = self.CurrentMember.getEncryptedPassword(oldPassword, self.AppConfig.EncryptionKey)
			if oldEncryptedPassword == self.CurrentMember.Password and newPassword:
				passwordChanged = self.CurrentMember.setPassword(newPassword, self.AppConfig.EncryptionKey)
				if passwordChanged:
					self.CurrentMember.flushCache()
					self.redirect("/Account/View")
				else:
					self.Model.update({
						'error': _("Un unforseen error occured! Your password could not be changed. You should contact the site administrator about this problem.")
						})
					self.render('views/account-changePassword.html')
			else:
				self.Model.update({
					'error': _("Changing password failed! You have either not entered a new password or the old one does not match.")
					})
				self.render('views/account-changePassword.html')
		else: self.requestLogin()

class Home(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			BeginnerBook = []
			BeginnerBookmark = []
			hasReadWrookForBeginners = False 
			# Refactor: Put in a cached method
			# BeginnerBook = Book.all().filter("Slug =", "wrook-for-beginners").fetch(limit=1)
			# if len(BeginnerBook) > 0:
				# BeginnerBookmark = Bookmark.all().filter("Reader = ", self.CurrentMember).filter("Book =", BeginnerBook[0]).fetch(limit=1)
			# if len(BeginnerBookmark) > 0:
				# hasReadWrookForBeginners = True

			cacheKey = "wrookMemberPosts-%s" % self.CurrentMember.key()
			posts = memcache.get(cacheKey)
			if not posts:
				posts = self.CurrentMember.ReceivedStoryPosts.order("-WhenOccured").fetch(limit=50)
				memcache.add(cacheKey, posts)

			self.Model.update({
				"posts": posts,
				"hasReadWrookForBeginners": hasReadWrookForBeginners
				})
			self.render('views/memberHome.html')
		else:
			self.render('views/visitorHome.html')

class MembersFeed(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			member = membership.Member.get(key)
			if member:
				self.setVisitedMember(member)
				posts = member.ReceivedStoryPosts.order("-WhenOccured").filter("Member = ", member.key()).fetch(limit=40)
				self.Model.update({
					"posts": posts
					})
				self.render('views/members-stories.html')
			else: self.error(404)
		else: self.requestLogin()

class ViewBook(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			#Before loading a book from the key, lets try to find it from the Slug
			book = Book.all().filter("Slug =", key).fetch(limit=1)
			if len(book) > 0: book = book[0]
			else: book = Book.get(key)
			if book:
				chapters = Chapter.all().filter("Book =", book).order("Number").fetch(limit=999)
				chapterCount = len(chapters)
				if book.Author:
					self.setVisitedMember(book.Author)
					userIsAuthor = (self.CurrentMember.key() == book.Author.key())
				else: userIsAuthor = False
				if userIsAuthor or self.CurrentMember.isAdmin: userCanEdit = True
				else: userCanEdit = False
				self.Model.update({
					"book": book,
					"chapters": chapters,
					"firstChapter": book.firstChapter(),
					"chapterCount": chapterCount,
					"userIsAuthor": userIsAuthor,
					"userCanEdit": userCanEdit
					})
				self.render('views/books-view.html')
			else: self.error(404)
		else: self.requestLogin()


class MembersProfile(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			visitedMember = membership.Member.get(key)
			if visitedMember:
				self.setVisitedMember(visitedMember)
				self.Model.update({
					"now": datetime.datetime.now()
					})
				self.render('views/MembersProfile.html')
			else: self.error(404)
		else: self.requestLogin()

#TODO: Refactor -  Put back in the chapter object
def deleteChapter(chapter):
	db.delete(chapter.Feedback)
	db.delete(chapter.Revisions)
	db.delete(chapter.Bookmarks)
	db.delete(chapter)

#TODO: Refactor -  Put back in the book object
def deleteBook(book):
	for chapter in book.Chapters:
		deleteChapter(chapter)
	db.delete(book.Feedback)
	db.delete(book.Bookmarks)
	db.delete(book)

class DeleteChapter(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			chapter = Chapter.get(key)
 			if chapter:
				userIsAuthor = (self.CurrentMember.key() == chapter.Book.Author.key())
				if userIsAuthor:
					self.Model.update({"chapter": chapter})
					self.render('views/deleteChapter.html')
				else: return
			else: self.error(404)
		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			chapter = Chapter.get(key)
			if chapter:
	 			userIsAuthor = (self.CurrentMember.key() == chapter.Book.Author.key())
				if userIsAuthor:
					if (self.request.get("doDelete") != "" and self.request.get("confirmDelete") == "yes"):
						deleteChapter(chapter)
						self.redirect("/Books/%s" % chapter.Book.key())
					else:
						self.redirect("/Chapter/Delete/%s" % chapter.key())
				else: return
			else: self.error(404)
		else: self.requestLogin()

class PasswordSent(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		member = membership.Member.get(key)
		if member:
			self.Model.update({"member": member})
			self.render('views/passwordSent.html')
		else: self.error(404)

class ResetPassword(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if key:
			member = membership.Member.get(key)
			if member:
				member.resetPassword(self.AppConfig.EncryptionKey)
				self.Model.update({"member": member})
				self.redirect('/PasswordSent/%s' % member.key())
			else: self.error(404)
		else:
			self.render("views/resetPassword.html")

	def post(self, key):
		onRequest(self)
		if not key:
			usernameOrEmail = self.request.get("usernameOrEmail")
			if usernameOrEmail:
				member = membership.getMemberFromCredentials(usernameOrEmail)
				if member:
					member.resetPassword(self.AppConfig.EncryptionKey)
					self.Model.update({"member": member})
					self.redirect('/PasswordSent/%s' % member.key())
				else:
					self.Model.update({"error": _("No member found with this username or email address!")})
					self.render("views/resetPassword.html")
			else:
				self.Model.update({"error": _("No member found with this username or email address!")})
				self.render("views/resetPassword.html")
		else: self.error(404)

class DeleteBook(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key)
			if book:
	 			userIsAuthor = (self.CurrentMember.key() == book.Author.key())
				if userIsAuthor:
					self.Model.update({"book": book})
					self.render('views/deleteBook.html')
				else: return
			else: self.error(404)
		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key)
			if book:
	 			userIsAuthor = (self.CurrentMember.key() == book.Author.key())
				if userIsAuthor:
					if (self.request.get("doDelete") != "" and self.request.get("confirmDelete") == "yes"):
						deleteBook(book)
						self.redirect("/")
					else:
						self.redirect("/Books/Delete/%s" % book.key())
				else: return
			else: self.error(404)
		else: self.requestLogin()
	
class ViewChapter(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			chapter = Chapter.get(key)
			if chapter:
				userIsAuthor = (self.CurrentMember.key() == chapter.Book.Author.key())
				self.Model.update({
					"chapter": chapter,
					"userIsAuthor": userIsAuthor
					})
				chapter.setBookmark(self.CurrentMember)
				self.render('views/viewChapter.html')
			else: self.error(404)
		else: self.requestLogin()


class EditChapterOptions(WrookRequestHandler):
	def get( self, key ):
		onRequest(self)
		if self.CurrentMember:
			chapter = Chapter.get(key)
			if chapter:
				form = ChapterForm(instance=chapter)
				self.Model.update({
					"chapter": chapter,
					"form": form
					})
				self.render('views/books-chapter-edit.html')
			else: self.error(404)
		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			chapter = Chapter.get(key)
			if chapter:
				if self.request.get("doDelete"):
					self.redirect('/Chapter/Delete/%s' % chapter.key())
					return
				form = ChapterForm(data=self.request.POST, instance=chapter)
				if form.is_valid():
					# Save the form, and redirect to the view page
					entity = form.save(commit=False)
					entity.put()
					self.redirect('/ViewChapter/%s' % chapter.key())
				else:
					self.Model.update({
						'chapter': chapter,
						'form': form
						})
					self.render('views/books-chapter-edit.html')
			else: self.error(404)
		else: self.requestLogin()

class Books(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			stage = self.request.get("stage")
			self.Model.update({
				'true': True,
				'false': False
				})
			if stage:
				self.Model.update({'books': Book.all().filter("Stage =", stage)})
				self.Model.update({'stage': stage})
			else:
				self.Model.update({'books': Book.all()})
			self.render('views/books.html')
		else: self.requestLogin()

class Books_Edit(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			if key == "": book = Book(Author=self.CurrentMember)
			else: book = Book.get(key) 
			form = BookForm(instance=book)
			self.Model.update({
				'book': book,
				'form': form
				})
			self.render('views/books-edit.html')
		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			if key == "": book = Book(Author=self.CurrentMember)
			else: book = Book.get(key) 
			form = BookForm(data=self.request.POST, instance=book)
			if form.is_valid():
				# Save the form, and redirect to the view page
				entity = form.save(commit=False)
				entity.put()
				if key == "": self.redirect('/NewChapter/%s' % book.key())
				else: self.redirect('/Books/%s' % book.key())
			else:
				self.Model.update({
					'book': book,
					'form': form
					})
				self.render("views/books-edit.html")
		else: self.requestLogin()

class Book_ReorderChapters(WrookRequestHandler):
	def get(self, key):
		chapterCount = utils.buildCountingList(50)
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key)
			if book:
				self.Model.update({
					'chapterCount': chapterCount,
					'book': book,
					'chapters': book.Chapters.order("Number")
					})
				self.render('views/books-reorderChapters.html')
			else: self.error(404)
		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			chapterCount = utils.buildCountingList(50)
			book = Book.get(key)
			if book:
				for chapter in book.Chapters.order("Number"):
					chapterSet = self.request.get("chapter.%s" % chapter.key())
					title = self.request.get("chapter.%s.title" % chapter.key())
					name = self.request.get("chapter.%s.name" % chapter.key())
					order = self.request.get("chapter.%s.order" % chapter.key())
					if chapterSet:
						if chapter.Name: chapter.Name = name
						else: chapter.Name = "Unnamed chapter"
						chapter.Title = title
						chapter.Number = int(order)
					chapter.put()
				if self.request.get("update"):
					self.Model.update({
						'chapterCount': chapterCount,
						'book': book,
						'chapters': book.Chapters.order("Number")
						})
					self.render('views/books-reorderChapters.html')
				if self.request.get("done"):
					self.redirect('/Books/%s' % book.key())
			else: self.error(404)
		else: self.requestLogin()

class Books_Edit_License(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key)
			if book:
				form = BookLicenseForm(instance=book)
				self.Model.update({
					'book': book,
					'form': form
					})
				self.render('views/books-edit-license.html')
			else: self.error(404)
		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key) 
			if book:
				form = BookLicenseForm(data=self.request.POST, instance=book)
				if form.is_valid():
					# Save the form, and redirect to the view page
					entity = form.save(commit=False)
					entity.put()
					self.redirect('/Books/%s' % book.key())
				else:
					self.Model.update({
						'book': book,
						'form': form
						})
					self.render("views/books-edit-license.html")
			else: self.error(404)
		else: self.requestLogin()

class Members(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			members = membership.Member.all().fetch(limit=200)
			self.Model.update({'members': members})
			self.render('views/members.html')
		else: self.requestLogin()

class MembersCoversList(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			visitedMember = membership.Member.get(key)
			if visitedMember:
				self.setVisitedMember(visitedMember)
				sharedCovers = visitedMember.Covers.filter("isSharedWithEveryone =", True).fetch(limit=100)
				privateCovers = visitedMember.Covers.filter("isSharedWithEveryone =", False).fetch(limit=100)
				permissionMemberCanSeePrivateCovers = self.CurrentMember.isAdmin or self.CurrentMember == self.VisitedMember
				self.Model.update({
					'sharedCovers': sharedCovers,
					'privateCovers': privateCovers,
					'permissionMemberCanSeePrivateCovers': permissionMemberCanSeePrivateCovers
					})
				self.render('views/members-covers-list.html')
			else: self.error(404)
		else: self.requestLogin()

class MembersBooksList(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			visitedMember = membership.Member.get(key)
			if visitedMember:
				self.setVisitedMember(visitedMember)
				books = visitedMember.Books.fetch(limit=999)
				self.Model.update({
					'books': books
					})
				self.render('views/members-books-list.html')
			else: self.error(404)
		else: self.requestLogin()

class MembersReadingsList(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			visitedMember = membership.Member.get(key)
			if visitedMember:
				self.setVisitedMember(visitedMember)
				bookmarks = visitedMember.Bookmarks.fetch(limit=999)
				self.Model.update({
					'bookmarks': bookmarks
					})
				self.render('views/members-bookmarks-list.html')
			else: self.error(404)
		else: self.requestLogin()


class BookReaders(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({'book': Book.get(key)})
			self.render('views/readers.html')
		else: self.requestLogin()

class NewChapter(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key)
			if book:
				chapter = Chapter(Book=book)
				form = ChapterFormForCreate(instance=chapter)
				self.Model.update({
					'book': book,
					'form': form
					})
				self.render('views/books-chapter-new.html')
			else: self.error(404)
		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key)
			if book:
				chapter = Chapter(Book=book)
				form = ChapterFormForCreate(data=self.request.POST, instance=chapter)
				if form.is_valid():
					# Save the form, and redirect to the view page
					entity = form.save(commit=False)
					entity.put()
					self.redirect("/Typewriter/%s" % chapter.key())
				else:
					self.Model.update({
						'form': form,
						'book': book
						})
					self.render("views/books-chapter-new.html")
			else: self.error(404)
		else: self.requestLogin()
			
class FeedbackBook(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key)
			if book:
				messages = book.Feedback.order("-Sent")
				self.Model.update({
					'book': book,
					'messages': messages,
					'targetType': 'book'
					})
				self.render('views/messages.html')
			else: self.error(404)
		else: self.requestLogin()


class Revisions_List(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			chapter = Chapter.get(key)
			if chapter:
				self.Model.update({
					'chapter': chapter,
					'revisions': chapter.Revisions.order("-Version").fetch(limit=999)
					})
				self.render('views/revisions-list.html')
			else: self.error(404)
		else: self.requestLogin()

class Revisions_View(WrookRequestHandler):
	def get(self, key, version):
		onRequest(self)
		if self.CurrentMember:
			chapter = Chapter.get(key)
			if chapter:
				revision = chapter.Revisions.filter("Version =", int(version)).fetch(limit=1)
				if len(revision) > 0:
					self.Model.update({
						'chapter': chapter,
						'revision': revision[0]
						})
					self.render('views/revisions-view.html')
				else: self.error(404)
			else: self.error(404)
		else: self.requestLogin()

class PostMessage(WrookRequestHandler):
	def post(self):
		onRequest(self)
		if self.CurrentMember:
			topic = self.request.get("Topic")
			if topic == "":
				topic = None
			text = self.request.get("Text")
			targetType = self.request.get("TargetType")
			isPrivate = (self.request.get("isPrivate") == "true")
			if targetType == "book":
				book = db.get(self.request.get("Book"))
				if book:
					author = book.Author
					message = Message(
						Book = book,
						Author = author,
						From = self.CurrentMember,
						Topic = topic,
						Text = text,
						isPrivate = isPrivate,
						targetType = targetType
						)
					message.put()
					story = StoryMemberPostMessageToABook()
					occurence = story.createOccurence({
						"member": self.CurrentMember,
						"message": message,
						"book": book
						})
					occurence.publish()
					self.redirect(self.request.get("ComebackUrl"))
				else: self.error(404)
			else: self.error(404)
		else: self.requestLogin()

class DeleteMessage(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			message = db.get(key)
			if message:
				if message.From.key() == self.CurrentMember.key():
					message.delete()
				self.redirect(self.request.get("ComebackUrl"))
			else: self.error(404)
		else: self.requestLogin()

class Typewriter(WrookRequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			chapter = Chapter.get(key)
			if chapter:
				self.Model.update({"chapter": chapter})
				self.render('views/typewriter.html')
			else: self.error(404)
		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			text = self.request.get("text")
			chapter = Chapter.get(key)
			if chapter:
				chapter.addRevision(text)
				self.redirect("/ViewChapter/%s" % chapter.key())
			else: self.error(404)
		else: self.requestLogin()

class AdminCommands(WrookRequestHandler):
	def get(self):
		onRequest(self)
#		if self.CurrentMember:
		self.render('views/admin-commands.html')
#		else: self.requestLogin()

	def post(self, key):
		onRequest(self)
#		if self.CurrentMember:
		if (key == "doDefaultAllBookStatus"):
			operationResults = self.doDefaultAllBookStatus()
		if (key == "doDefaultAllChapterNumberTo0"):
			operationResults = self.doDefaultAllChapterNumberTo0()
		if (key == "doLoadLicenseTypes"):
			operationResults = self.doLoadLicenseTypes()
		if (key == "doSetEncryptionKey"):
			operationResults = self.doSetEncryptionKey()
		else:
			operationResults = CommandResult(ErrorCode=1, Message=_("No commands have been processed. Missing parameters!"))
		self.Model.update({"operationResults": operationResults})
		self.render('views/admin-commands.html')
#		else: self.requestLogin()
	
	def doDefaultAllBookStatus(self):
		for book in Book.all():
			if book.Stage == "planning": book.Stage = "writing"
			for chapter in book.Chapters:
				if chapter.Stage == "planning": chapter.Stage = "writing"
				chapter.put()
			book.put()
		result = CommandResult(ErrorCode=0, Message=_("Empty status properties of all books and chapters have been defaulted!"))
		return result

	def doSetEncryptionKey(self):
		appConfig = getWrookAppConfig()
		appConfig.EncryptionKey = self.request.get("encryptionKey")
		appConfig.put()
		result = CommandResult(ErrorCode=0, Message=_("The new encryption key has been set!"))
		return result

	def doLoadLicenseTypes(self):
		licensing.LoadLicenseTypes()
		result = CommandResult(ErrorCode=0, Message=_("All license types have been loaded into the database!"))
		return result

	def doDefaultAllChapterNumberTo0(self):
		for chapter in Chapter.all():
			chapter.Number=0
			chapter.put()
		result = CommandResult(ErrorCode=0, Message=_("All chapter numbers have been reseted to 0!"))
		return result

class CommandResult(db.Model):
	ErrorCode = db.IntegerProperty(default="0") # 0 = no errors
	Message = db.TextProperty(default="")

class Command(db.Model):
	Title = db.StringProperty(default="")
	Description = db.TextProperty(default="")
	Code = db.TextProperty(default="")

class FlushCache(WrookRequestHandler):
	def get(self):
		onRequest(self)
#		if self.CurrentMember:
		memcache.flush_all()
		#TODO: Refactor - Use the proforma module for a confirmation
		self.response.out.write(_("Congratulations... you flushed the cache!"))
		#Post this as a story for admins
		story = StorySiteCacheIsFlushed()
		occurence = story.createOccurence({"member": self.CurrentMember })
		occurence.publish()
#		else: self.requestLogin()

class Test(WrookRequestHandler):
	def get(self):
		import _runtest
		self.response.out.write(_runtest.getTestResults())

def getDefaultTheme(): #TODO: Refactor -  Move back to the Customize module??
	defaultTheme = memcache.get("wrookDefaultTheme")
	if not defaultTheme:
		defaultMoments = Moment.all().filter("isDefault =", True).order("-Priority").fetch(limit=1)
		if len(defaultMoments)==0:
			return None
		else:
			defaultTheme = defaultMoments[0].Theme
			memcache.add("wrookDefaultTheme", defaultTheme)
	return defaultTheme

class SetDefaultTheme(WrookRequestHandler): #TODO: Refactor -  Move back to the Customize module
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			theme = customize.Theme.get(self.request.get("selectedTheme"))
			if theme and self.CurrentMember.isAdmin:
				db.delete(Moment.all().filter("isDefault =", True)) # Removes the current default moments
				moment = Moment(
					Title = "Default moment",
					Theme = theme,
					isDefault = True
					)
				moment.put()
				memcache.delete("wrookDefaultTheme") # Invalidates the cached default theme
				self.redirect("/Themes")
			else: self.error(500)
		else: self.requestLogin()

class WrookApplication(webapp.Application): # decouppling for future use
	pass

#============================================================================
# ABOUT

class About_HalfBakedEdition(WrookRequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-halfBakedEdition.html")

class About_OpenSoureLicense(WrookRequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-openSourceLicense.html")

class About_OpenSoureAttribution(WrookRequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-openSourceAttribution.html")

class About_CPAL(WrookRequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-CPAL.html")

class About_who(WrookRequestHandler):
	def get(self):
		onRequest(self)
		self.render("views/about-who.html")


class Suggestions(WrookRequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			self.render("views/member-suggestions.html")
		else: self.requestLogin()
		


#============================================================================
# STORIES

class StoryMemberStartReadingBook(stories.Story):
	ID = "MemberStartReadingBook"
	TitleTemplate = _('<a href="/Members/$MemberKey">$MemberFullname</a> started reading <a href="/Books/$BookKey">$BookTitle</a>')
	BodyTemplate = ""
	Icon = "book-open.png"

	def getTitle(self, params):
		member = params["member"]
		book = params["book"]
		data = {
			"MemberFullname": member.fullname(),
			"MemberKey": member.key(),
			"BookTitle": book.Title,
			"BookKey": book.key()
			}
		template = Template(self.TitleTemplate)
		return template.safe_substitute(data)

	def getTargets(self, params): #Get the list of member who will receive the story posts
		targets = []
		targets.append(params["book"].Author)
		targets.append(params["member"])
		return targets

class StoryMemberPostMessageToABook(stories.Story):
	ID = "MemberPostMessageToABook"
	TitleTemplate = _('<a href="/Members/$MemberKey">$MemberFullname</a> left a comment on <a href="/Books/$BookKey">$BookTitle</a>')
	BodyTemplate = _('''
<a href="/Feedback/Book/$BookKey" style="float: right; margin-left: 15px;">
	<img width="45" src="$CoverImage"/>
</a>
<a href="/Members/$MemberKey" style="float: left; margin-right: 15px;">
	<img width="30" src="$MemberAvatar"/>
</a>
<strong><a href="/Feedback/Book/$BookKey">The message</a> said: $MessageTitle </strong><br />"&#160;$MessageBody&#160;"
''')
	Icon = "comment.png"

	def getTitle(self, params):
		member = params["member"]
		book = params["book"]
		data = {
			"MemberFullname": member.fullname(),
			"MemberKey": member.key(),
			"BookTitle": book.Title,
			"BookKey": book.key()
			}
		template = Template(self.TitleTemplate)
		return template.safe_substitute(data)

	def getBody(self, params):
		member = params["member"]
		message = params["message"]
		book = params["book"]
		data = {
			"MemberFullname": member.fullname(),
			"MemberAvatar": member.gravatar30(),
			"MemberKey": member.key(),
			"BookTitle": book.Title,
			"BookKey": book.key(),
			"CoverImage": book.getCover().thumbURL45(),
			"MessageTitle": message.Topic,
			"MessageBody": message.Text
			}
		template = Template(self.BodyTemplate)
		return template.safe_substitute(data)

	def getTargets(self, params): #Get the list of member who will receive the story posts
		targets = []
		targets.append(params["book"].Author)
		targets.append(params["member"])
		return targets

# This story warns all admins that the site cache has been flushed
class StorySiteCacheIsFlushed(stories.Story):
	ID = "SiteCacheIsFlushed"
	TitleTemplate = _('<a href="/Members/$MemberKey">$MemberFullname</a> has flushed the site cache')
	BodyTemplate = ""
	Icon = "flush.png"

	def getTitle(self, params):
		member = params["member"]
		data = {
			"MemberFullname": member.fullname(),
			"MemberKey": member.key()
			}
		template = Template(self.TitleTemplate)
		return template.safe_substitute(data)

	def getTargets(self, params): #Get the list of member who will receive the story posts
		return membership.Member.all().filter("isAdmin =", True).fetch(limit=999)
		



#============================================================================

URLMappings = [
	( '/', Home),
	(r'/NewChapter/(.*)', NewChapter),
	(r'/ViewChapter/(.*)', ViewChapter),
	(r'/Chapter/Delete/(.*)', DeleteChapter),
	(r'/EditChapter/(.*)', EditChapterOptions),
	(r'/Typewriter/(.*)', Typewriter),
	(r'/Feedback/Book/(.*)', FeedbackBook),
	(r'/Feedback/Delete/(.*)', DeleteMessage),
	( '/PostMessage', PostMessage),
	(r'/Join/(.*)', Join), #TODO: Refactor -  Should this be moved in the membership module?
	( '/EditAccount', EditAccount), #TODO: Refactor -  Should this be moved in part in the membership module?
	( '/Account/View', AccountView),
	( '/Account/ChangeProfilePhoto', AccountChangeProfilePhoto),
	( '/Account/ChangePassword', AccountChangePassword),
	( '/Books', Books),
	( '/Books/', Books),
	(r'/Books/Edit/License/(.*)', Books_Edit_License),
	(r'/Books/Edit/(.*)', Books_Edit),
	(r'/Books/SetCover/(.*)', BookSetCover),
	(r'/Books/ReorderChapters/(.*)', Book_ReorderChapters),
	(r'/Books/Delete/(.*)', DeleteBook),
	(r'/Books/Chapters/(.*)/Rev/(.*)', Revisions_View),
	(r'/Books/Chapters/(.*)/Rev', Revisions_List),
	(r'/Books/(.*)', ViewBook),
	( '/Members', Members),
	(r'/Members/(.*)/Covers', MembersCoversList),
	(r'/Members/(.*)/Books', MembersBooksList),
	(r'/Members/(.*)/Readings', MembersReadingsList),
	(r'/Members/(.*)/Profile', MembersProfile),
	(r'/Members/(.*)', MembersFeed),
	(r'/Readers/Book/(.*)', BookReaders),
	( '/Covers/', CoverList),
	(r'/Covers/Thumbnail/(.*)', CoverThumbnail),
	(r'/Covers/Image/(.*)', CoverImage),
	(r'/Covers/Edit/(.*)', CoverEdit),
	(r'/Covers/Share/(.*)', CoverShare),
	(r'/Covers/Unshare/(.*)', CoverUnshare),
	( '/Covers/SetDefault', CoverSetDefault),
	( '/Covers/Select', CoverSelect),
	(r'/Covers/(.*)', CoverView),
	( '/SetDefaultTheme', SetDefaultTheme),
	( '/Admin/Commands', AdminCommands), # Refactor: move to an admin module?
	( '/Login', Login), # Refactor: move to the membership module?
	( '/Logout', Logout), # Refactor: move to the membership module?
	( '/Customize', Customize),
	(r'/PasswordSent/(.*)', PasswordSent),
	(r'/ResetPassword/(.*)', ResetPassword),
	( '/About/OpenSourceAttribution', About_OpenSoureAttribution),
	( '/About/OpenSourceLicense', About_OpenSoureLicense),
	( '/About/CPAL', About_CPAL),
	( '/About/Who', About_who),
	( '/About/Half-Baked-Edition', About_HalfBakedEdition),
	( '/Suggestions', Suggestions),
	(r'/Admin/Commands/(.*)', AdminCommands), # Refactor: move to an admin module?
	( '/FlushCache', FlushCache), # Refactor: move to an admin module?
	( '/Test', Test) # Refactor: move to an admin module?
]

# Integrate the Labs module
URLMappings += stories.URLMappings()
stories.onRequest = onRequest

# Integrate the Labs module
URLMappings += labs.URLMappings()
labs.onRequest = onRequest

# Integrates the Customize module
URLMappings += customize.URLMappings()
customize.onRequest = onRequest

# Integrates the Membership module
URLMappings += membership.URLMappings()
membership.onRequest = onRequest

# Integrates the Membership module
URLMappings += proforma.URLMappings()
proforma.onRequest = onRequest

# Integrate the Talk module
URLMappings += talk.URLMappings()
talk.onRequest = onRequest

application = WrookApplication(URLMappings, debug=True) # Instantiate the main application

# Application constants
#TODO: This is not secure, put in the app config
picnikKey = "eb44efec693047ac4f4b2a429bc0be5a" # Developper Key for the Picnik API

class WrookAppConfig(db.Model):
	DefaultCover = db.ReferenceProperty(Cover, verbose_name=_("Default cover"))
	EncryptionKey = db.StringProperty(verbose_name=_("Encryption key")) # Used when a scecret key is needed for encrypting passwords and other data

def getWrookAppConfig():
	wrookAppConfig = memcache.get("wrookAppConfig")
	if not wrookAppConfig:
		cfg = WrookAppConfig.all().fetch(limit=1)
		if len(cfg) == 1:
			wrookAppConfig = cfg[0]
			memcache.add("wrookAppConfig", wrookAppConfig)
	return wrookAppConfig

def real_main():
	sys.path.append(os.path.dirname(__file__))
	sys.path.append(os.path.join(os.path.dirname(__file__), 'feathers'))
	logging.getLogger().setLevel(logging.DEBUG)
	webapp.run(application)

def profile_log_main():
	# This is the main function for profiling 
	# We've renamed our original main() above to real_main()
	import cProfile, pstats, StringIO
	prof = cProfile.Profile()
	prof = prof.runctx("real_main()", globals(), locals())
	stream = StringIO.StringIO()
	stats = pstats.Stats(prof, stream=stream)
	stats.sort_stats("time")  # Or cumulative
	stats.print_stats(80)  # 80 = how many to print
	# The rest is optional.
	# stats.print_callees()
	# stats.print_callers()
	logging.info("Profile data:\n%s", stream.getvalue())

def profile_html_main():
	# This is the main function for profiling 
	# We've renamed our original main() above to real_main()
	import cProfile, pstats
	prof = cProfile.Profile()
	prof = prof.runctx("real_main()", globals(), locals())
	print "<div style='text-align:left;font-size:1.1em; color: #000; background: #fff; padding: 20px;'><pre>"
	stats = pstats.Stats(prof)
	#stats.sort_stats("time")  # Or cumulative
	stats.sort_stats("cumulative")  # Or cumulative
	stats.print_stats(300)  # 80 = how many to print
	# The rest is optional.
	# stats.print_callees()
	# stats.print_callers()
	print "</pre></div>"

main = real_main

if __name__ == '__main__':
	main()
