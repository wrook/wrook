import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.utils import simplejson
from google.appengine.ext import db
from feathers import webapp, membership


def URLMappings():
	return [
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

def getReplies(parent):
	return Reply.all().ancestor(parent).order("Sent").fetch(limit=999)

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

