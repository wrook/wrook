import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.utils import simplejson
from google.appengine.ext import db
from feathers import webapp, membership


def URLMappings():
	return [
		(r'/Talk/Post/(.*)/Reply/MiniForm/JSON', ReplyMiniFormJSON)
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
	Topic = db.ReferenceProperty(Topic, collection_name="Replies", required=True)

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
			self.response.out.write(simplejson.dumps(data))
		else: self.response.out.write(simplejson.dumps({"errorCode":1004, "errorMessage": _("You must be logged in to post a comment.")}))

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			pass

