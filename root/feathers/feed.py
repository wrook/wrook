from google.appengine.ext import db, webapp
from feathers import membership

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

def createStoryOccurence(StoryClass, referenceValues): #factory pattern to instanciate a StoryOccurence
	storyOccurence = StoryOccurence()
	storyOccurence.Story = StoryClass()
	return storyOccurence

class Story:
	ID = ""
	TitleTemplate = ""
	BodyTemplate = ""
	Icon = "" 

	def getTitle(StoryOccurence):
		pass
		
	def getBody(StoryOccurence):
		pass
		
	def publish(StoryOccurence): #Start or continue the publishing of StoryFeedPosts
		pass

class StoryOccurence(db.Expando):
	Story = None #The reference story of this occurence
	StoryID = db.StringProperty(required=True)
	Title = db.StringProperty(default="")
	Body = db.TextProperty(default="")
	Icon = db.StringProperty(default="")
	WhenOccured = db.DateTimeProperty()
	WhenCreated = db.DateTimeProperty(auto_now_add=True)
	lastPublishedMemberTimestamp = db.DateTimeProperty()
	isDonePublishing = db.BooleanProperty(default=False)

	def update(): # updates the TitleTemplate and BodyTemplate according to the new reference values
		pass
	def publish():
		pass

class StoryPost(db.Expando):
	Story = None #The reference story of this occurence
	StoryOccurence = db.ReferenceProperty(StoryOccurence, collection_name="FeedPosts")
	StoryID = db.StringProperty(required=True)
	Member = db.ReferenceProperty(membership.Member, collection_name="FeedPosts")
	Title = db.StringProperty(default="")
	Body = db.TextProperty(default="")
	Icon = db.StringProperty(default="")
	WhenOccured = db.DateTimeProperty()
	WhenPublished = db.DateTimeProperty(auto_now_add=True)
	Importance = db.IntegerProperty(default=0) #specific to the each users

