#!python
# coding=UTF-8

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.utils import simplejson
from google.appengine.ext import db
from google.appengine.ext.webapp import template
#Django imports
from django.utils import translation
from django.utils.translation import gettext as _

import webapp
import membership
import cachetree

import logging

maxRecentReplies = 3
maxRecentTopics = 5
maxTopicsPerPage = 20

currentRequestHandler = None

def URLMappings():
	return [
		(r'/Talk/Topic/New/(.*)/', handler_topic_new),
		(r'/Talk/Topic/(.*)/Delete/JSON', handler_topic_delete_JSON),
		(r'/Talk/Topic/(.*)/', handler_topic_view),
		(r'/Talk/Reply/New/(.*)/', handler_reply_new),
		(r'/Talk/Post/(.*)/Reply/MiniForm/JSON', handler_reply_miniForm_JSON),
		(r'/Talk/Post/(.*)/Reply/MiniForm/JSON/Post', handler_reply_miniForm_JSON_post)
	]

def onRequest(request): # Event triggering to let the host application intervene
	pass


class Replyable(cachetree.Cachable):

#	def old_replies(self, maxResults=999, offset=0):
#		key = "replyable-%s::repliesList-%s-%s" % (self.key(), maxResults, offset)
#		replies = cachetree.get(key)
#		if not replies:
#			replies = Reply.all().ancestor(self).order("Sent")\
#				.fetch(limit=maxResults, offset=offset)
#			cachetree.set(key, replies)
#		return replies
	
	def replies(self, maxResults=999, offset=0):
		logging.debug("in: replies(%s)" % self.key())
		cacheKey = "%s-replies-list-%s-%s" % (self.key(), maxResults, offset)
		replies = cachetree.get_fresh_cache(cacheKey,[
			"%s-replies" % self.key()])
		logging.debug("replies: %s " % replies)
		if not replies:
			replies = Reply.all().ancestor(self).order("Sent")\
				.fetch(limit=maxResults, offset=offset)
			cachetree.set(cacheKey, replies)
		logging.debug("out: replies(%s)" % self.key())
		return replies

	def recent_replies(self, maxResults=maxRecentReplies):
		replies = Reply.all().ancestor(self).order("-Sent")
		return replies.fetch(limit=maxResults)
	
	def render_replies_list(self, maxResults=999, offset=0):
		logging.debug("in: render_replies_list(%s)" % self.key())
		cacheKey = "%s-render-replies-list-%s-%s" % (self.key(), maxResults, offset)
		renderedReplies = cachetree.get_fresh_cache(cacheKey,[
			"%s-replies" % self.key()])
		if not renderedReplies:
			templateSource = "%s/views/talk-part-replies.html" % os.path.dirname(__file__)
			model = {"replies": self.replies(maxResults, offset)}
			renderedReplies = template.render(templateSource, model)
			cachetree.set(cacheKey, renderedReplies)
		logging.debug("out: render_replies_list(%s)" % self.key())
		return renderedReplies.decode('utf-8')
	
	def render_more_replies_link(self, offset):
		templateSource = "%s/views/talk-part-showMoreReplies.html" % os.path.dirname(__file__)
		model = {"parent": self}
		return template.render(templateSource, model)
	
	def has_more_replies(self):
		'''Returns true if the item has more replies than the number of recent replies shown by default.'''
		return len(self.replies(1, maxRecentReplies)) == 1
		#TODO: Optimize with a sharded counter
	
	def render_recent_replies(self, maxResults=maxRecentReplies):
		templateSource = "%s/views/talk-part-replies.html" % os.path.dirname(__file__)
		model = {
			"replies": self.recent_replies(maxResults),
			"renderedShowMoreRepliesLink": self.render_more_replies_link( maxResults)
			}
		return template.render(templateSource, model).decode('utf-8')
	
	def render_reply_form(self, model={}):
		if webapp.currentRequest:
			model.update(webapp.currentRequest.Model)
		model.update({'parent': self})
		templateSource = "%s/views/talk-part-replyForm.html" % os.path.dirname(__file__)
		return template.render(templateSource, model).decode('utf-8')
	
	def unread_replies(self):
		return self.replies.filter("isRead =", False).fetch(limit=999)
	
	def touch_up(self, childItem):
		if childItem:
			if childItem.__class__.__name__ == "Reply":
				cachetree.touch("%s-replies" % self.key())
			super(Replyable, self).touch_up(childItem)

class Topicable(cachetree.Cachable):
	
	def topics(self, maxResults=999, offset=0):
		key = "topicable-%s::topics-%s-%s" % (self.key(), maxResults, offset)
		topics = cachetree.get(key)
		if not topics:
			topics = Topic.all().ancestor(self).order("-Sent")\
				.fetch(limit=maxResults, offset=offset)
			cachetree.set(key, topics)
		return topics
	
	def render_recent_topics_list(self, maxResults=maxRecentTopics):
		return self.render_topics_list(maxResults)
	
	def render_topics_list(self, maxResults=maxTopicsPerPage, offset=0):
		cacheKey = "%s-renderedTopicList-%s-%s" % (self.key(), maxResults, offset)
		renderedTopicList = cachetree.get_fresh_cache(cacheKey,
			["%s-topicsWithReplies" % self.key()])
		if not renderedTopicList:
			templateSource = "%s/views/talk-part-topics.html" % os.path.dirname(__file__)
			model = {"topics": self.topics(maxResults)}
			renderedTopicList = template.render(templateSource, model)
			cachetree.set(cacheKey, renderedTopicList)
		return renderedTopicList.decode('utf-8')
	
	def render_topic_form(self, model={}):
		if webapp.currentRequest:
			model.update(webapp.currentRequest.Model)
		model.update({'parent': self})
		return webapp.render("talk-part-topicForm.html", model)
	
	def touch_up(self, childItem):
		if childItem:
			if childItem.__class__.__name__ == "Reply":
				cachetree.touch("%s-topicsWithReplies" % self.key())
			elif childItem.__class__.__name__ == "Topic":
				cachetree.touch("%s-topicsWithReplies" % self.key())
				cachetree.touch("%s-topics" % self.key())
			super(Topicable, self).touch_up(childItem)


class Post(db.Model):
	From = db.ReferenceProperty(
		membership.Member,
		collection_name="Posts",
		required=True)
	Body = db.TextProperty()
	Sent = db.DateTimeProperty(auto_now_add=True)
	isPrivate = db.BooleanProperty(default=False)
	# Only the target of the post see's the message

class Topic(Post, Replyable):
	Title = db.StringProperty()
	ReplyCount = db.IntegerProperty(default=0)
	
	def permalink(self):
		return "/Talk/Topic/%s/" % self.key()
	
	def render(self):
		cacheKey = "topic-%s" % self.key()
		renderedTopic = cachetree.get(cacheKey)
		if not renderedTopic:
			templateSource = "%s/views/talk-part-topic.html" % os.path.dirname(__file__)
			data = {"topic": self}
			renderedTopic = template.render(templateSource, data)
			cachetree.set(cacheKey, renderedTopic)
		return renderedTopic

class Reply(Post, cachetree.Cachable):
	
	def permalink(self):
		return "%s#%s" % (parent.permalink(), self.key())
	
	def renderBasic(self, request):
		request.Model.update({"reply": self})
		request.TemplateBaseFolder = os.path.dirname(__file__)
		return request.getRender("views/talk-part-replies.html")
	
	def render(self):
		templateSource = "%s/views/talk-part-reply.html" % os.path.dirname(__file__)
		data = {"reply": self}
		return template.render(templateSource, data)

def delete_topic(topic):
	topic.clear_cache()
	#TODO: The following two delete operations shoulod run in a transaction
	replies = topic.replies()
	if replies:	db.delete(replies)
	db.delete(topic)
	return True
	

class handler_topic_delete_JSON(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			if key:
				topic = Topic.get(key)
				if topic:
					if delete_topic(topic):
						data = {"errorCode":0, "html": _("Topic has been deleted...")}
						self.response.out.write("(%s)" % simplejson.dumps(data))
					else:
						self.response.out.write(simplejson.dumps({
							"errorCode": 1,
							"errorMessage": _("An error occured! Sorry!")
							}))
				else:
					#TODO: This error block should not be repeted manually
					self.response.out.write(simplejson.dumps({
						"errorCode": 1,
						"errorMessage": _("An error occured! Sorry!")
						}))
		
		else:
			self.response.out.write(simplejson.dumps({
				"errorCode":1004,
				"errorMessage": _("You must be logged in to post a comment.")
				}))

class handler_reply_miniForm_JSON(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			self.Model.update({
				"key": key,
				"postURL": "/Talk/Post/%s/Reply/MiniForm" % key
			})
			self.TemplateBaseFolder = os.path.dirname(__file__)
			html = self.getRender("views/talk-comment-miniForm.html")
			data = {"errorCode":0, "html":html}
			self.response.out.write("(%s)" % simplejson.dumps(data))
		else:
			self.response.out.write(simplejson.dumps({
				"errorCode":1004,
				"errorMessage": _("You must be logged in to post a comment.")
				}))

class handler_topic_view(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if key:
			cacheKey = key
			logging.debug("getting topic from cache: %s" % key)
			topic = cachetree.get(cacheKey)
			if not topic:
				logging.debug("no topic found in cache")
				topic = Topic.get(key)
				if topic: cachetree.set(key, topic)
			if topic:
				cacheKey = "%s-page-TopicView"\
					% topic.key()
				cachedPage = cachetree.get_fresh_cache(
					cacheKey,
					["%s" % topic.parent().key(),
						"%s-replies" % topic.key()])
				if not cachedPage:
					self.Model.update({
						"topic" : topic,
						"renderedReplies" : topic.render_replies_list(),
						"renderedReplyForm" : topic.render_reply_form()
					})
					self.TemplateBaseFolder = os.path.dirname(__file__)
					cachedPage = self.getRender('views/talk-TopicView.html')
					cachetree.set(cacheKey, cachedPage)
				self.response.out.write(cachedPage)
			else: self.error(404)
		else: self.error(500)

class handler_topic_new(webapp.RequestHandler):
	def get(self, key):
		self.post(key)
	
	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			parent = db.get(key)
			title = self.request.get("title")
			body = self.request.get("body")
			if parent:
				topic = Topic(
					parent = parent,
					Title = title,
					Body = body,
					From = self.CurrentMember
					)
				topic.put()
				topic.touch()
				#TODO: This story has been disable because of package dependency problems... needs to be resolved
				#Post this as a story and publish
#				StoryMemberPostsTopicOnBook().createOccurence({
#					"member": self.CurrentMember,
#					"topic": topic,
#					"parentURL": parentURL,
#					"parentTitle": parentTitle,
#					"recipient": recipient
#					}).publish()
				self.response.out.write(topic.render())
			else:
				self.error(404)
		else:
			self.response.out.write(simplejson.dumps({
				"errorCode":1004,
				"errorMessage": _("You must be logged in to post a comment.")
				}))

class handler_reply_new(webapp.RequestHandler):
	def get(self, key):
		self.post(key)
	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			parent = db.get(key)
			body = self.request.get("body")
			if parent:
				reply = Reply(
					parent = parent,
					Body = body,
					From = self.CurrentMember
					)
				reply.put()
				logging.debug("new reply = %s" % reply.key())
				logging.debug("reply object = %s" % reply)
				reply.touch()
				#TODO: This story has been disable because of package dependency problems... needs to be resolved
				#Post this as a story and publish
#				StoryMemberPostsTopicOnBook().createOccurence({
#					"member": self.CurrentMember,
#					"topic": topic,
#					"parentURL": parentURL,
#					"parentTitle": parentTitle,
#					"recipient": recipient
#					}).publish()
				self.response.out.write(reply.render())
			else:
				self.error(404)
		else:
			self.response.out.write(simplejson.dumps({
				"errorCode":1004,
				"errorMessage": _("You must be logged in to post a reply.")
				}))

class handler_reply_miniForm_JSON_post(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			parentEntity = db.get(key)
			commentBody = self.request.get("commentBody")
			if parentEntity:
				if commentBody:
					reply = Reply(
						parent = parentEntity,
						From = self.CurrentMember,
						Body = commentBody)
					reply.put()
					reply.touch()
					self.response.out.write("(%s)" % simplejson.dumps({
						"errorCode":0,
						"html": reply.renderBasic(self)
						}))
				else: #Return empty html is the reply body was empty
					self.response.out.write(simplejson.dumps({
						"errorCode":0
						}))
			else: self.error(404)
		else:
			self.response.out.write(simplejson.dumps({
				"errorCode":1004,
				"errorMessage": _("You must be logged in to post a comment.")
				}))

