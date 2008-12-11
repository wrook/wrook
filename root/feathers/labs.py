#!python
# coding=UTF-8

import os, cgi, datetime, logging
import markdown2
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from feathers import webapp, membership

maxVotesPerMembers = 3 # Constantfor the maximum number of votes which a user can cast at any moment (doesnt included votes for implemented features)

def URLMappings():
	return [
		( '/Labs', Labs),
		( '/Labs/Submit', Submit),
		(r'/Labs/Feature/View/(.*)', ViewFeature),
		(r'/Labs/Feature/Vote/(.*)', CastVote),
		(r'/Labs/Feature/MarkAsDone/(.*)', MarkFeatureAsDone),
		(r'/Labs/Feature/Delete/(.*)', DeleteFeature),
		(r'/Labs/Feature/RetractVote/(.*)', RetractVote)
	]

def onRequest(request): # Event triggering to let the host application intervene
	pass


class Release(db.Model):
	Created = db.DateTimeProperty(auto_now_add=True)
	Released = db.DateTimeProperty()
	Planned = db.DateTimeProperty()
	MajorVersion = db.IntegerProperty()
	MinorVersion = db.IntegerProperty()
	Description = db.TextProperty()

class Feature(db.Model):
	Type = db.StringProperty(required=True, choices=set(["newfeature", "improvement", "bugfix"]))
	Title = db.StringProperty()
	Description = db.TextProperty()
	Created = db.DateTimeProperty(auto_now_add=True)
	Proposed = db.DateTimeProperty()
	Done = db.DateTimeProperty()
	isDone = db.BooleanProperty()
	isDiscarded = db.BooleanProperty(default=False)
	WhyIsDiscarded = db.TextProperty()
	Release = db.ReferenceProperty(Release, collection_name="Features")
	VoteCount = db.IntegerProperty(default=0)
	
	def markdownDescription(self):
		return markdown2.markdown(self.Description)

	def markAsDone(self):
		self.isDone = True
		self.Done = datetime.datetime.now()
		for vote in self.Votes:
			vote.isDone = True
			vote.put()
		self.put()
	
class Vote(db.Model):
	Member = db.ReferenceProperty(membership.Member, collection_name="Votes")
	Feature = db.ReferenceProperty(Feature, collection_name="Votes")
	Created = db.DateTimeProperty(auto_now_add=True)
	Comment = db.TextProperty()
	isDone = db.BooleanProperty(default=False)

def countVotesLeft(Member):
	voteCount = Vote.all().filter("Member =", Member).filter("isDone =", False).count()
	voteCount = maxVotesPerMembers - voteCount
	return voteCount

class Labs(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			for feature in Feature.all():
				if feature.isDone != True:
					feature.isDone = False
					feature.put()
			yourVotes = Vote.all().filter("Member =", self.CurrentMember).order("isDone").fetch(limit=999)
			completedFeatures = Feature.all().filter("isDone =", True).order("-Done")
			notCompletedFeatures = Feature.all().filter("isDone =", False).order("-VoteCount").order("-Created")
			memberVotesLeft = countVotesLeft(self.CurrentMember)
			self.Model.update({
				"features": notCompletedFeatures,
				"completedFeatures": completedFeatures,
				"yourVotes": yourVotes,
				"memberVotesLeft": memberVotesLeft
			})
			self.TemplateBaseFolder = os.path.dirname(__file__)
			self.render('views/labs.html')

class Submit(webapp.RequestHandler):
	def post(self):
		onRequest(self)
		if self.CurrentMemberMember:
			type = self.request.get("Type")
			title = self.request.get("Title")
			description = self.request.get("Description")
			feature = Feature(
				Type = type,
				Title = title,
				Description = description,
				Proposed = datetime.datetime.now(),
				VoteCount = 1
				)
			feature.put()
			vote = Vote(
				Member = self.CurrentMemberMember,
				Feature = feature
				)
			vote.put()
			self.Model.update({"feature": feature})
			self.TemplateBaseFolder = os.path.dirname(__file__)
			self.render('views/labs-submit.html')


class ViewFeature(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			feature = Feature.get(key)
			memberHasVotesLeft = (countVotesLeft(self.CurrentMember) > 0)
			memberHasVoted = len(Vote.all().filter("Member =", self.CurrentMember).filter("Feature =", feature).fetch(limit=1))
			self.Model.update({
				"feature": feature,
				"memberHasVoted": memberHasVoted,
				"memberHasVotesLeft": memberHasVotesLeft
				})
			self.TemplateBaseFolder = os.path.dirname(__file__)
			self.render('views/labs-viewFeature.html')

class CastVote(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			feature = Feature.get(key)
			vote = Vote(
				Member = self.CurrentMember,
				Feature = feature
				)
			vote.put()
			if feature.VoteCount != None: feature.VoteCount = feature.VoteCount + 1
			else: feature.VoteCount = 1
			feature.put()
			self.redirect("/Labs/Feature/View/%s" % feature.key())

class MarkFeatureAsDone(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			feature = Feature.get(key)
			feature.markAsDone()
			self.redirect("/Labs/Feature/View/%s" % feature.key())
		
class DeleteFeature(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			feature = Feature.get(key)
			db.delete(feature.Votes)
			db.delete(feature)
			self.redirect("/Labs")
		
class RetractVote(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			feature = db.get(key)
			db.delete(Vote.all().filter("Member =", self.CurrentMember).filter("Feature =", feature))
			if feature.VoteCount != None: feature.VoteCount = feature.VoteCount - 1
			else: feature.VoteCount = 0
			feature.put()
			self.redirect("/Labs/Feature/View/%s" % feature.key())


