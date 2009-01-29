#!python
# coding=UTF-8

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings

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
		(r'/Members/(.*)/Follow', MembersFollow),
		(r'/Members/(.*)/StopFollowing', MembersStopFollowing),
		(r'/Members/(.*)', MembersFeed),
		( '/Customize', Customize),
		( '/Suggestions', Suggestions)]


class Home(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			self.setVisitedMember(self.CurrentMember)
			BeginnerBook = []
			BeginnerBookmark = []
			
			cacheKey = "wrookMemberPosts-%s" % self.CurrentMember.key()
			posts = memcache.get(cacheKey)
			if not posts:
				posts = self.CurrentMember.ReceivedStoryPosts.order("-WhenOccured").fetch(limit=50)
				memcache.add(cacheKey, posts)
			
			self.Model.update({
				"posts": posts
				})
			self.render2('views/memberHome.html')
		else:
			self.render2('views/visitorHome.html')

class MembersFeed(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		member = membership.Member.get(key)
		if member:
			self.setVisitedMember(member)
			posts = member.ReceivedStoryPosts.order("-WhenOccured").filter("Member = ", member.key()).fetch(limit=40)
			self.Model.update({
				"posts": posts
				})
			self.render2('views/members-stories.html')
		else: self.error(404)

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
		visitedMember = membership.Member.get(key)
		if visitedMember:
			self.setVisitedMember(visitedMember)
			self.Model.update({
				"now": datetime.datetime.now()
				})
			self.render2('views/MembersProfile.html')
		else: self.error(404)

class MembersFollow(webapp.RequestHandler):
	def get(self, key):
		from django.utils import simplejson
		onRequest(self)
		member = membership.Member.get(key)
		if self.CurrentMember!=None and member!=None:
			newRelationship = self.CurrentMember.start_follower_relationship_with(member)
			if newRelationship:
				data = {"errorCode":0, "html": _("Done!")}
				self.response.out.write("(%s)" % simplejson.dumps(data))
			else:
				self.response.out.write(simplejson.dumps({
					"errorCode": 1,
					"errorMessage": _("An error occured! Sorry!")
					}))
		else:
			self.response.out.write(simplejson.dumps({
				"errorCode": 1,
				"errorMessage": _("An error occured! Sorry!")
				}))

class MembersStopFollowing(webapp.RequestHandler):
	def get(self, key):
		from django.utils import simplejson
		onRequest(self)
		member = membership.Member.get(key)
		if self.CurrentMember!=None and member!=None:
			result = self.CurrentMember.stop_follower_relationship_with(member)
			if result:
				data = {"errorCode":0, "html": _("Done!")}
				self.response.out.write("(%s)" % simplejson.dumps(data))
			else:
				self.response.out.write(simplejson.dumps({
					"errorCode": 1,
					"errorMessage": _("An error occured! Sorry!")
					}))
		else:
			self.response.out.write(simplejson.dumps({
				"errorCode": 1,
				"errorMessage": _("An error occured! Sorry!")
				}))

def get_featured_members():
	return membership.Member.all().filter("hasProfilePhoto =", True).fetch(limit=5)

def get_search_members(searchCriteria):
	import logging
	logging.debug("criteria: %s" % searchCriteria)
	return membership.Member.all().search(searchCriteria).fetch(limit=40)

class Members(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		searchCriteria = self.request.get("searchCriteria")
		if searchCriteria: members = get_search_members(searchCriteria)
		else: members = get_featured_members()
		self.Model.update({
			'members': members,
			'searchCriteria': searchCriteria})
		self.render2('views/members.html')

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
				self.render2('views/members-covers-list.html')
			else: self.error(404)
		else: self.requestLogin()

class MembersBooksList(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		visitedMember = membership.Member.get(key)
		if visitedMember:
			self.setVisitedMember(visitedMember)
			books = visitedMember.Books.fetch(limit=999)
			hasEditRights = False # Getting rights should be refactored.. this is half-assed
			if (self.CurrentMember!=None) & (visitedMember!=None):
				hasEditRights = self.CurrentMember.isAdmin or self.CurrentMember == self.VisitedMember
			self.Model.update({
				'hasEditRights': hasEditRights,
				'books': books
				})
			self.render2('views/members-books-list.html')
		else: self.error(404)

class MembersReadingsList(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			visitedMember = membership.Member.get(key)
			if visitedMember:
				self.setVisitedMember(visitedMember)
				bookmarks = visitedMember.Bookmarks.fetch(limit=999)
				books = []
				following = visitedMember.get_relationships_members_from("follower")
				followers = visitedMember.get_relationships_members_to("follower")
				for bookmark in bookmarks:
					books.append(bookmark.Book)
				self.Model.update({
					'following': following,
					'followers': followers,
					'bookmarks': bookmarks,
					'books': books
					})
				self.render2('views/members-bookmarks-list.html')
			else: self.error(404)
		else: self.requestLogin()

