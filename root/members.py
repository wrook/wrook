#!python
# coding=UTF-8

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.api import memcache
from feathers import webapp
from feathers import membership

def URLMappings():
	return [
		( '/', Home),
		( '/Members', Members),
		(r'/Members/(.*)/Covers', MembersCoversList),
		(r'/Members/(.*)/Books', MembersBooksList),
		(r'/Members/(.*)/Readings', MembersReadingsList),
		(r'/Members/(.*)/Profile', MembersProfile),
		(r'/Members/(.*)', MembersFeed),
		(r'/Readers/Book/(.*)', BookReaders),
		( '/Customize', Customize),
		( '/Suggestions', Suggestions)]


class Home(webapp.RequestHandler):
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

class MembersFeed(webapp.RequestHandler):
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

class Customize(webapp.RequestHandler):
	def get(self):
		from feathers import customize
		import books
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({
				"latestCovers": books.Cover.all().fetch(limit=3),
				"latestThemes": customize.Theme.all().fetch(limit=3)
				})
			self.render("views/customize.html")

class Suggestions(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			self.render("views/member-suggestions.html")
		else: self.requestLogin()

class MembersProfile(webapp.RequestHandler):
	def get(self, key):
		import datetime
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

class Members(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			members = membership.Member.all().fetch(limit=200)
			self.Model.update({'members': members})
			self.render('views/members.html')
		else: self.requestLogin()

class MembersCoversList(webapp.RequestHandler):
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

class MembersBooksList(webapp.RequestHandler):
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

class MembersReadingsList(webapp.RequestHandler):
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

class BookReaders(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({'book': Book.get(key)})
			self.render('views/readers.html')
		else: self.requestLogin()

