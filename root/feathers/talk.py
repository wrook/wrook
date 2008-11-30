import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.utils import simplejson
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from feathers import webapp, membership, stories
from string import Template
#TODO: This template import should become useless after rafactoring the Stories module..


def URLMappings():
	return [
		(r'/Talk/Topic/New/(.*)/', Topic_New),
		(r'/Talk/Topic/(.*)/', Topic_View),
		(r'/Talk/Reply/New/(.*)/', Reply_New),
		(r'/Talk/Post/(.*)/Reply/MiniForm/JSON', ReplyMiniFormJSON),
		(r'/Talk/Post/(.*)/Reply/MiniForm/JSON/Post', ReplyMiniFormJSONPost)
	]

def onRequest(request): # Event triggering to let the host application intervene
	pass


class Post(db.Model):
	From = db.ReferenceProperty(membership.Member, collection_name="Posts", required=True)
	Body = db.TextProperty()
	Sent = db.DateTimeProperty(auto_now_add=True)
	isPrivate = db.BooleanProperty(default = False) # Only the target of the post see's the message

class Topic(Post):
	Title = db.StringProperty()
	ReplyCount = db.IntegerProperty(default=0)

	def unreadReplies(self):
		return self.Replies.filter("isRead =", False)


class Reply(Post):
	#Topic = db.ReferenceProperty(Topic, collection_name="Replies", required=True)
	
	def renderBasic(self, request):
		request.Model.update({"reply": self})
		request.TemplateBaseFolder = os.path.dirname(__file__)
		return request.getRender("views/talk-part-replies.html")
		

def getTopics(parent, maxResults=999):
	return Topic.all().ancestor(parent).order("-Sent").fetch(limit=maxResults)

def getReplies(parent, maxResults=999):
	return Reply.all().ancestor(parent).order("Sent").fetch(limit=maxResults)

def renderTopicsList(parent, maxResults=999):
	templateSource = "%s/views/talk-part-topics.html" % os.path.dirname(__file__)
	data = {"topics": getTopics(parent, maxResults)}
	return template.render(templateSource, data)

def renderRepliesList(parent, maxResults=999):
	templateSource = "%s/views/talk-part-replies.html" % os.path.dirname(__file__)
	data = {"replies": getReplies(parent, maxResults)}
	return template.render(templateSource, data)

def renderTopic(topic):
	templateSource = "%s/views/talk-part-topic.html" % os.path.dirname(__file__)
	data = {
		"topic": topic
	}
	return template.render(templateSource, data)

def renderReply(reply):
	templateSource = "%s/views/talk-part-reply.html" % os.path.dirname(__file__)
	data = {
		"reply": reply
	}
	return template.render(templateSource, data)

def renderTopicForm(parentKey, data):
	templateSource = "%s/views/talk-part-topicForm.html" % os.path.dirname(__file__)
	return template.render(templateSource, data)

def renderReplyForm(parentKey, data):
	templateSource = "%s/views/talk-part-replyForm.html" % os.path.dirname(__file__)
	return template.render(templateSource, data)

class ReplyMiniFormJSON(webapp.RequestHandler):
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


class Topic_View(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			topic = Topic.get(key)
			if topic:
				replyFormData = {
					'parentKey': topic.key(),
					'parentTitle': topic.Title,
					'parentURL': '/Books/%s' % topic.key(),
					'recipient': topic.From.key()
				}
				replyFormData.update(self.Model)
				renderedReplyForm = renderReplyForm(topic, replyFormData)
				self.Model.update({
					'topic': topic,
					'renderedReplies': renderRepliesList(topic),
					'renderedReplyForm': renderedReplyForm
					})
				self.TemplateBaseFolder = os.path.dirname(__file__)
				self.render('views/talk-TopicView.html')
			else: self.error(404)
		else: self.requestLogin()

class Topic_New(webapp.RequestHandler):
	def get(self, key):
		self.post(key)
	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			parent = db.get(key)
			title = self.request.get("title")
			body = self.request.get("body")
			parentTitle = self.request.get("parentTitle")
			parentURL = self.request.get("parentURL")
			recipient = self.request.get("recipient")
			if parent:
				topic = Topic(
					parent = parent,
					Title = title,
					Body = body, 
					From = self.CurrentMember
					)
				topic.put()
				#Post this as a story and publish
				StoryMemberPostsTopicOnBook().createOccurence({
					"member": self.CurrentMember,
					"topic": topic,
					"parentURL": parentURL,
					"parentTitle": parentTitle,
					"recipient": recipient
					}).publish()
				self.response.out.write(renderTopic(topic))
			else:
				self.error(404)
		else:
			self.response.out.write(simplejson.dumps({
				"errorCode":1004,
				"errorMessage": _("You must be logged in to post a comment.")
				}))

class Reply_New(webapp.RequestHandler):
	def get(self, key):
		self.post(key)
	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			parent = db.get(key)
			body = self.request.get("body")
			parentTitle = self.request.get("parentTitle")
			parentURL = self.request.get("parentURL")
			recipient = self.request.get("recipient")
			if parent:
				reply = Reply(
					parent = parent,
					Body = body, 
					From = self.CurrentMember
					)
				reply.put()
				#Post this as a story and publish
#				StoryMemberPostsTopicOnBook().createOccurence({
#					"member": self.CurrentMember,
#					"topic": topic,
#					"parentURL": parentURL,
#					"parentTitle": parentTitle,
#					"recipient": recipient
#					}).publish()
				self.response.out.write(renderReply(reply))
			else:
				self.error(404)
		else:
			self.response.out.write(simplejson.dumps({
				"errorCode":1004,
				"errorMessage": _("You must be logged in to post a reply.")
				}))

class ReplyMiniFormJSONPost(webapp.RequestHandler):
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

class StoryMemberPostsTopicOnBook(stories.Story):
	ID = "MemberPostsTopicOnBook"
	TitleTemplate = _('<a href="/Members/$MemberKey">$MemberFullname</a> has posted a new topic under <a href="ParentURL">$ParentTitle</a>')
	BodyTemplate = _('''
<strong>The message said: $TopicTitle </strong>
<br />"&#160;$TopicBody&#160;"
''')
	Icon = "comment.png"

	#The way by which the data "property bag" is handled is needlessly
	#Cumbersome... this should be simplified
	def getTitle(self, params):
		member = params["member"]
		parentURL = params["parentURL"]
		parentTitle = params["parentTitle"]
		data = {
			"MemberFullname": member.fullname(),
			"MemberKey": member.key(),
			"ParentTitle": parentTitle,
			"ParentURL": parentURL
			}
		template = Template(self.TitleTemplate)
		return template.safe_substitute(data)

	def getBody(self, params):
		member = params["member"]
		topic = params["topic"]
		parentURL = params["parentURL"]
		parentTitle = params["parentTitle"]
		data = {
			"MemberFullname": member.fullname(),
			"MemberAvatar": member.gravatar30(),
			"MemberKey": member.key(),
			"ParentTitle": parentTitle,
			"ParentURL": parentURL,
			"TopicTitle": topic.Title,
			"TopicBody": topic.Body
			}
		template = Template(self.BodyTemplate)
		return template.safe_substitute(data)

	def getTargets(self, params): #Get the list of member who will receive the story posts
		targets = []
		if params["recipient"]:
			targets.append(membership.Member.get(params["recipient"]))
		targets.append(params["member"])
		return targets

