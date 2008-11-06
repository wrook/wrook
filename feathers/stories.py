import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.utils import simplejson
from google.appengine.ext import db
from google.appengine.api import memcache
from feathers import webapp, membership, talk

# FEED Module for Google App Engine

# Story types and descriptions:
# - An author has revised a chapter you had already read
# - An author has published a new chapter and you can continue your reading
# - An author has changed the overall editing stage of his book
# - A reader has left feedback on your book/chapter
# - You have gained a new reader
# - You have gained a new reader for book XXX
# - Reader has finished reading your book
# - A friend has accepted your invitation
# - A member you had invited has joined Wrook
# - An author you have read has started a new books
# - A book you where reading has been deleted
# - The wrook team has released a new feature
# - Special announcement from the Wrook Team

# Typical Expando properties shared by StoryInstance and StoryFeedPost
# - RefWhen
# - RefMember
# - RefReader
# - RefAuthor
# - RefBook
# - RefChapter
# - RefRevision
# - RefBookmark
# - RefMessage
# - RefInvite
# - RefFeature
# - RefVote
# - RefTheme

def URLMappings():
	return [
		(r'/Stories/Reply/(.*)', StoryPostReply),
		(r'/Stories/Post/(.*)/Delete/JSON', StoryPostDeleteJSON)
	]

def onRequest(request): # Event triggering to let the host application intervene
	pass

class Story:
	ID = ""
	TitleTemplate = ""
	BodyTemplate = ""
	Icon = ""

	def getTitle(self, params):
		return self.TitleTemplate
		
	def getBody(self, params):
		return self.BodyTemplate

	def getTargets(self, occurence): #Get the list of member who will receive the story posts
		return None

	def createOccurence(self, params): #factory pattern to instanciate a StoryOccurence
		occurence = StoryOccurence(
			StoryID = self.ID,
			Icon = self.Icon,
			FromMember = params["member"]
			)
		occurence.Story = self
		occurence.setParams(params)
		occurence.put()
		return occurence

class StoryOccurence(db.Model):
	Story = None #The reference story of this occurence
	StoryID = db.StringProperty(required=True)
	Title = db.StringProperty(default="")
	Body = db.TextProperty(default="")
	Icon = db.StringProperty(default="")
	FromMember = db.ReferenceProperty(membership.Member, collection_name="OwnStoryOccurences")
	WhenOccured = db.DateTimeProperty(auto_now_add=True)
	WhenCreated = db.DateTimeProperty(auto_now_add=True)
	lastPublishedMemberTimestamp = db.DateTimeProperty()
	isDonePublishing = db.BooleanProperty(default=False)

	Params = {}

	def setParams(self, params): # updates the TitleTemplate and BodyTemplate according to the new reference values
		self.Params = params
		self.Title = self.Story.getTitle(params)
		self.Body = self.Story.getBody(params)

	def publish(self):
		targets = self.Story.getTargets(self.Params)
		for target in targets:
			self.createPostForMember(target)
		self.isDonePublishing = True
		self.put()

	def createPostForMember(self, member):
		post = StoryPost(
			StoryID = self.Story.ID,
			StoryOccurence = self,
			Member = member,
			Title = self.Title,
			Body = self.Body,
			Icon = self.Icon,
			FromMember = self.FromMember,
			WhenOccured = self.WhenOccured)
		post.Story = self.Story
		post.put()
		return post

class StoryPostTopic(talk.Topic):
	isRead = db.BooleanProperty(default = False) # The author has forced this message to be private

class StoryPost(db.Model):
	Story = None #The reference story of this occurence
	StoryID = db.StringProperty(required=True)
	StoryOccurence = db.ReferenceProperty(StoryOccurence, collection_name="Posts")
	FromMember = db.ReferenceProperty(membership.Member, collection_name="OwnStoryPosts")
	Member = db.ReferenceProperty(membership.Member, collection_name="ReceivedStoryPosts")
	Title = db.StringProperty(default="")
	Body = db.TextProperty(default="")
	Icon = db.StringProperty(default="")
	WhenOccured = db.DateTimeProperty()
	WhenPublished = db.DateTimeProperty(auto_now_add=True)
	Importance = db.IntegerProperty(default=0) #specific to the each users
	Topic = db.ReferenceProperty(StoryPostTopic, collection_name="StoryPost")


class StoryPostReply(webapp.RequestHandler):
	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			storyPost = StoryPost.get(key)
			comment = self.request.get("comment")
			if storyPost and comment:
				topics = storyPost.Topics.fetch(limit=1)
				if len(topics) > 0: topic = topics[0]
				else:
					topic = StoryPostTopic(
						parent = storyPost,
						Title = storyPost.Title,
						From = storyPost.Member)
					topic.isRead = False
					topic.put()
				reply = talk.Reply(
					parent = topic,
					Topic = topic,
					From = self.CurrentMember,
					Body = comment)
				reply.put()
				if storyPost.Member.key() == self.CurrentMember.key():
					self.redirect("/")
				else: self.redirect("/Members/%s" % storyPost.Member.key())
			else: self.error(404)
		else: self.requestLogin()

class StoryPostDeleteJSON(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			storyPost = StoryPost.get(key)
			if storyPost:
				member = storyPost.Member
				if member.key() == self.CurrentMember.key():
					topic = storyPost.Topic
					if topic:
						db.delete(topic.Replies)
						db.delete(topic)
					db.delete(storyPost)
					memcache.delete("wrookMemberPosts-%s" % member.key())
					
					self.response.out.write(simplejson.dumps({"errorCode":0}))
				else: self.response.out.write(simplejson.dumps({"errorCode":1002, "errorMessage": _("Sorry, you do not have the right to delete this item.")}))
			else: self.response.out.write(simplejson.dumps({"errorCode":1001, "errorMessage": _("The item you tried to delete could not be found. Maybe it was already deleted.")}))
		else: self.response.out.write(simplejson.dumps({"errorCode":1003, "errorMessage": _("You must be logged in to delete this item.")}))

