#!python
# coding=UTF-8

#Django imports
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.utils import translation
from django.utils.translation import gettext as _
from django.conf import settings
##from django.db import models
#from django import forms

from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from google.appengine.api import memcache
from google.appengine.api import images

from feathers import webapp
from feathers import talk

import app

#===============================================================
# BOOK, CHAPTERS, REVISIONS, TYPEWRITER AND LICENSING


def URLMappings():
	return [
		(r'/NewChapter/(.*)', NewChapter),
		(r'/ViewChapter/(.*)', ViewChapter),
		(r'/Chapter/Delete/(.*)', DeleteChapter),
		(r'/EditChapter/(.*)', EditChapterOptions),
		(r'/Typewriter/(.*)', Typewriter),
		( '/Books', Books),
		( '/Books/', Books),
		(r'/Books/Edit/License/(.*)', Books_Edit_License),
		(r'/Books/Edit/(.*)', Books_Edit),
		(r'/Books/SetCover/(.*)', BookSetCover),
		(r'/Books/ReorderChapters/(.*)', Book_ReorderChapters),
		(r'/Books/Delete/(.*)', DeleteBook),
		(r'/Books/Chapters/(.*)/Rev/(.*)', Revisions_View),
		(r'/Books/Chapters/(.*)/Rev', Revisions_List),
		(r'/Books/(.*)/Talk', Books_Talk),
		(r'/Books/(.*)', ViewBook),
		( '/Covers/', CoverList),
		(r'/Covers/Thumbnail/(.*)', CoverThumbnail),
		(r'/Covers/Image/(.*)', CoverImage),
		(r'/Covers/Edit/(.*)', CoverEdit),
		(r'/Covers/Share/(.*)', CoverShare),
		(r'/Covers/Unshare/(.*)', CoverUnshare),
		( '/Covers/SetDefault', CoverSetDefault),
		( '/Covers/Select', CoverSelect),
		(r'/Covers/(.*)', CoverView)]

def deleteChapter(chapter):
	#TODO: Refactor -  Put back in the chapter object
	#TODO: Also delete topics
	db.delete(chapter.Revisions)
	db.delete(chapter.Bookmarks)
	db.delete(chapter)

def deleteBook(book):
	#TODO: Refactor -  Put back in the book object
	for chapter in book.Chapters:
		deleteChapter(chapter)
	#TODO: Also delete topics
	db.delete(book.Bookmarks)
	db.delete(book)

class Cover(db.Model):
	'''
	Cover image of a book.
	'''
	from feathers import membership
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

class Book(talk.Topicable):
	'''
	A book contributed by a member
	'''
	from feathers import membership
	import licensing
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
	
	def permalink(self):
		return "/Books/%s/" % self.key()
	
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
			appConfig = app.getWrookAppConfig()
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
		import markdown2
		return markdown2.markdown(self.AttribDetailed)

class Chapter(db.Model):
	'''
	Chapter of a book.
	'''
	Book = db.ReferenceProperty(Book, collection_name="Chapters")
	'''The parent Book of the chapter'''
	Number = db.IntegerProperty(default=0)
	'''Numeric index of the chapter compared to other chapters in the book'''
	Name = db.StringProperty(default=_("Chapter X"), required=True)
	'''Name of the chapter. Ex.: Chapter 2 (not to confuse with Title)'''
	Title = db.StringProperty(default="")
	'''Title of the chapter. Ex.: A dark and stormy night (not to be confused with Name)'''
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
		import wrookStories
		chapter = self
		bookmarks = Bookmark.all().filter("Reader =", member).filter("Book =", chapter.Book).fetch(limit=999)
		# If this is a first read, a story is posted
		if len(bookmarks) == 0:
			story = wrookStories.StoryMemberStartReadingBook()
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
			Reader = member)
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
		from feathers import utils
		if self.WordCount: return self.WordCount
		else:
			self.WordCount = utils.wordCount(self.Text)
			return self.WordCount
	
	def markdownText(self):
		import markdown2
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
	from feathers import membership
	Chapter = db.ReferenceProperty(Chapter, collection_name="Bookmarks")
	Book = db.ReferenceProperty(Book, collection_name="Bookmarks")
	Author = db.ReferenceProperty(membership.Member, collection_name="ReaderBookmarks")
	Reader = db.ReferenceProperty(membership.Member, collection_name="Bookmarks")
	When = db.DateTimeProperty(auto_now_add=True)

class BookForm(djangoforms.ModelForm):
	'''
	Form used to create a book or edit a books properties.
	'''
	class Meta:
		model = Book
		fields = ('Title', 'Stage', "Slug", 'Synopsis', 'NoteFromAuthor')

class BookLicenseForm(djangoforms.ModelForm):
	'''
	Form used to edit specifically the licensing properties of a book.
	'''
	class Meta:
		model = Book
		fields = ('License', 'AttribDetailed', 'AttribAuthorIsAuthor', 'AttribAuthorName')

class ChapterForm(djangoforms.ModelForm):
	'''
	Form used to create a chapter or edit its properties
	'''
	class Meta:
		model = Chapter
		fields = ("Name", "Title", "Stage", "Synopsis")

class ChapterFormForCreate(djangoforms.ModelForm):
	class Meta:
		model = Chapter
		fields = ("Name", "Title", "Stage")

class ViewBook(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			#Before loading a book from the key, lets try to find it from the Slug
			book = Book.all().filter("Slug =", key).fetch(limit=1)
			if len(book) > 0: book = book[0]
			else: book = Book.get(key)
			if book:
				#TODO: This should be methodized as ordered_chapters
				chapters = Chapter.all().filter("Book =", book).order("Number").fetch(limit=999)
				#TODO: This should be methodized as chapter_count
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

class DeleteChapter(webapp.RequestHandler):
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

class DeleteBook(webapp.RequestHandler):
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

class ViewChapter(webapp.RequestHandler):
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

class EditChapterOptions(webapp.RequestHandler):
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

class Books(webapp.RequestHandler):
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

class Books_Edit(webapp.RequestHandler):
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

class Books_Talk(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			book = Book.get(key)
			if book:
				self.Model.update({'book': book})
				self.render('views/books-talk.html')
			else: self.error(404)
		else: self.requestLogin()

class Book_ReorderChapters(webapp.RequestHandler):
	from feathers import utils
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
		from feathers import utils
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

class Books_Edit_License(webapp.RequestHandler):
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

class NewChapter(webapp.RequestHandler):
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

class Revisions_List(webapp.RequestHandler):
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

class Revisions_View(webapp.RequestHandler):
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

class Typewriter(webapp.RequestHandler):
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


#===============================================================
# BOOK COVERS


class CoverForm(djangoforms.ModelForm):
	class Meta:
		model = Cover
		fields = ("SampleTitle", "TitleColor", "isReusable")

class CoverSetDefault(webapp.RequestHandler):
	from feathers import proforma
	#TODO: Refactor -  should be secure for admins???
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

class BookSetCover(webapp.RequestHandler):
	def get(self, key):
		from feathers import proforma
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

class CoverEdit(webapp.RequestHandler):
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

class CoverThumbnail(webapp.RequestHandler):
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

class CoverImage(webapp.RequestHandler):
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
	

class CoverList(webapp.RequestHandler):
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

class CoverSelect(webapp.RequestHandler):
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

class CoverView(webapp.RequestHandler):
	def get(self, key):
		import app
		onRequest(self)
		if self.CurrentMember:
			cover = Cover.get(key)
			if cover:
				self.Model.update({
					'cover': cover,
					'picnikKey': app.picnikKey
					})
				self.render('views/covers-view.html')
			else: self.error(404)
		else: self.requestLogin()

class CoverShare(webapp.RequestHandler):
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

class CoverUnshare(webapp.RequestHandler):
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


