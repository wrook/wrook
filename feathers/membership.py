import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import cgi, datetime, logging, hashlib
from string import Template
from google.appengine.api import users, images, memcache, mail
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from django.utils.translation import gettext
from feathers import utils, webapp

# Not used anymore, but kept here as a reminder of how to get the hostname... remove later
#hostname = os.environ['HTTP_HOST'] 

def URLMappings():
	return [
		(r'/Invites', Invites),
		(r'/Invites/(.*)', InviteEdit),
		(r'/Membership/ProfilePhoto/Image/(.*)', ProfilePhotoImage)
	]

def onRequest(request): # Event triggering to let the host application intervene
	pass

loginErrorMessage = ""

def getMemberFromCredentials(username): # Username or Email
	#Refactor: The cookies should keep the member key for faster retrieval
	cacheKey = "wrookMember-%s" % username
	member = memcache.get(cacheKey)
	if not member:
		member = Member.all().filter("Username =", username).fetch(limit=1)
		if len(member)>0:
			member = member[0]
		else:
			member = Member.all().filter("Email =", username).fetch(limit=1)
			if len(member)>0:
				member = member[0]
			else: return False
	memcache.add(cacheKey, member)
	return member


def loginFromCookies(requestHandler):
	member = getMemberFromCredentials(requestHandler.request.cookies.get('username', ''))
	if not member:
		return None
	else:
		credentialsHash = requestHandler.request.cookies.get('credentialsHash', '')
		newCredentialsHash = hashlib.md5("%s"+member.Password % member.key()).hexdigest()
		if credentialsHash != newCredentialsHash:
			member.cancelLogin(requestHandler)
			return None
		else:
			return member

class LoginResult():
	def __init__(self, ErrorCode, ErrorMessage, Member):
		self.Member = Member
		self.ErrorCode = ErrorCode
		self.ErrorMessage = ErrorMessage
	
def memberLogin(requestHandler, username, password):
	member = getMemberFromCredentials(username)
	if not member:
		return LoginResult(1, _("Wrong username or bad password."), None)
	else:
		if not member.Password:
			return LoginResult(2, _('Your account does not have a password. Use the "Reset password" option to create a new one.'), None)
		else:
			if member.Password != password:
				return LoginResult(1, _("Wrong username or bad password."), None)
	member.login(requestHandler)
	return LoginResult(0, "", Member)

def logout(requestHandler):
	# Clears the login cookies
	requestHandler.response.headers.add_header('Set-Cookie', 'credentialsHash=%s; expires=Fri, 31-Dec-2020 23:59:59 GMT' % "")
	requestHandler.response.headers.add_header('Set-Cookie', 'username=%s; expires=Fri, 31-Dec-2020 23:59:59 GMT' % "")

class Member(db.Model):
	User = db.UserProperty()
	Username = db.StringProperty(default="...", required=True)
	Email = db.EmailProperty(default="...", required=True)
	ProfilePhoto = db.BlobProperty(verbose_name="Profile photo")
	isEmailValidated = db.BooleanProperty(required=True, default=False)
	WhenEmailValidated = db.DateTimeProperty()
	Firstname = db.StringProperty(required=True)
	Password = db.StringProperty(default="")
	Lastname = db.StringProperty(required=True)
	Gender = db.StringProperty(default=None, choices=set([None, "male", "female"]))
	Birthdate = db.DateProperty()
	PreferedLanguage = db.StringProperty(required=True, default="en")
	About = db.TextProperty()
	isReader = db.BooleanProperty(default=False)
	isAuthor = db.BooleanProperty(default=False)
	Created = db.DateTimeProperty(auto_now_add=True)
	isAdmin = db.BooleanProperty(default=False)

	def currentThemeSelection(self):
		cacheKey = "wrookMemberThemeSelection-%s" % self.key()
		selection = memcache.get(cacheKey)
		if not selection:
			selection = self.ThemeSelections.order("-WhenSelected").fetch(1)[0]
			memcache.add(cacheKey, selection)
		return selection

	def preferedLanguageName(self):
		if self.PreferedLanguage == "en": return _("English")
		if self.PreferedLanguage == "fr": return _("French")
		else: return ""

	def genderName(self):
		if self.Gender == "male": return _("Male")
		if self.Gender == "female": return _("Female")
		else: return ""

	def login(self, requestHandler):
		credentialsHash = hashlib.md5("%s"+self.Password % self.key()).hexdigest()
		requestHandler.response.headers.add_header('Set-Cookie', 'credentialsHash=%s; expires=Fri, 31-Dec-2020 23:59:59 GMT' % credentialsHash)
		requestHandler.response.headers.add_header('Set-Cookie', 'username=%s; expires=Fri, 31-Dec-2020 23:59:59 GMT' % self.Username)

	def resetPassword(self):
		self.Password = utils.nicepass()
		self.put()

	def sendPassword(self):
		data = {
			"firstname": self.Firstname,
			"lastname": self.Lastname,
			"password": self.Password
			}
		messageTemplate = Template(_("""
Hello $firstname $lastname,

Here is your Wrook password: $password

We sent you this new password because you just joined Wrook or because you asked for a "reset password".

If you have any questions, dont hesitate to contact us by email at admin@wrook.org

Have a good day!
The Wrook Team
http://www.wrook.org

"""))
		message = mail.EmailMessage(
			sender = "admin@wrook.org",
			subject = _("About your Wrook.org account!"),
			reply_to = "admin@wrook.org",
			to = "%s %s <%s>" % (self.Firstname, self.Lastname, self.Email),
			body = messageTemplate.safe_substitute(data)
			)
		message.send()

	def cancelLogin(self, requestHandler):
		credentialsHash = hashlib.md5("%s"+self.Password % self.key()).hexdigest()
		requestHandler.response.headers.add_header('Set-Cookie', 'credentialsHash=;')
		requestHandler.response.headers.add_header('Set-Cookie', 'username=;')

	def isNew(self):
		booksCount = self.Books.all().count()
		bookmarksCount = self.Bookmarks.all().count()
		if (booksCount+bookmarksCount > 0): return False 
		else: return True

	def gravatar30(self):
		if self.ProfilePhoto: return "/Membership/ProfilePhoto/Image/%s?width=30" % self.key()
		else: return "/images/avatar.png"

	def gravatar50(self):
		if self.ProfilePhoto: return "/Membership/ProfilePhoto/Image/%s?width=50" % self.key()
		else: return "/images/avatar.png"

	def gravatar80(self):
		if self.ProfilePhoto: return "/Membership/ProfilePhoto/Image/%s?width=80" % self.key()
		else: return "/images/avatar.png"

	def gravatar100(self):
		if self.ProfilePhoto: return "/Membership/ProfilePhoto/Image/%s?width=100" % self.key()
		else: return "/images/avatar.png"

	def gravatar120(self):
		if self.ProfilePhoto: return "/Membership/ProfilePhoto/Image/%s?width=120" % self.key()
		else: return "/images/avatar.png"

	def fullname(self):
		return str(self.Firstname + " " + self.Lastname)

class Invite(db.Expando):
	FromMember = db.ReferenceProperty(Member, collection_name="SentInvites")
	AcceptedMember = db.ReferenceProperty(Member, collection_name="AcceptedInvite")
	Firstname = db.StringProperty(required=True, default=" ")
	Lastname = db.StringProperty(required=True, default=" ")
	Email = db.EmailProperty(required=True, default=" ")
	PersonalMessage = db.TextProperty()
	Status = db.StringProperty(required=True, default="notsent", choices=set(["notsent", "failed", "sent", "accepted", "resent", "discarded"]))
	WhenSent = db.DateTimeProperty(auto_now_add=True)
	WhenResent = db.DateTimeProperty()
	WhenAccepted = db.DateTimeProperty()

	def send(self):
		sendTo = "%s %s <%s>" % (self.Firstname, self.Lastname, self.Email)
		message = mail.EmailMessage(
			sender = "admin@wrook.org",
			subject = _("%s invites you to read a book!") % self.FromMember.fullname(),
			reply_to = self.FromMember.Email,
			to = sendTo,
			body = self.getMessage()
			)
		message.send()
		if self.Status == "sent":
			self.Status = "resent"
			self.WhenResent = datetime.datetime.now()
		else:
			self.Status = "sent"
		self.WhenSent = datetime.datetime.now()
		self.put()
		return self;

	def getMessage(self):
		if self.is_saved(): key = self.key()
		else: key = ""
		inviteData = {
			"firstname": self.Firstname,
			"lastname": self.Lastname,
			"senderName": self.FromMember.fullname(),
			"senderMessage": self.PersonalMessage,
			"inviteKey": key
			}
		if inviteData.get("senderMessage"):
			return self.inviteTemplateWithMessage.safe_substitute(inviteData)
		else:
			return self.inviteTemplate.safe_substitute(inviteData)

	inviteTemplateWithMessage = Template(_("""
Hello $firstname $lastname,

$senderName is inviting you to join the Wrook community.

Wrook is a community of writers and readers of all genre of literature. Read free books,
participate in the writting process of authors or publish and share your own writings.

A message from $senderName:
"$senderMessage"

To join, simply follow this link:
http://www.wrook.org/Join/$inviteKey

Thank you,
The Wrook Team
"""))

	inviteTemplate = Template(_("""
Hello $firstname $lastname,

$senderName is inviting you to join the Wrook community.

Wrook is a community of writers and readers of all genre of literature. Read free books,
participate in the writting process of authors or publish and share your own writings.

To join, simply follow this link:
http://www.wrook.org/Join/$inviteKey

Thank you,
The Wrook Team
"""))


class Invites(webapp.RequestHandler):
	def get(self):
		onRequest(self)
		if self.CurrentMember:
			invites = self.CurrentMember.SentInvites
			if self.CurrentMember.isAdmin:
				allInvites = Invite.all()
				self.Model.update({"allInvites": allInvites})
			self.Model.update({"invites": invites})
			self.TemplateBase = os.path.dirname(__file__)
			self.render('views/membership-invites.html')

class InviteForm(djangoforms.ModelForm):
	class Meta:
		model = Invite
		fields = ("Firstname","Lastname","Email", "PersonalMessage")


class InviteEdit(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		if self.CurrentMember:
			if key: invite = Invite.get(key)
			else: invite = Invite(FromMember = self.CurrentMember)
			if invite:
				form = InviteForm(instance=invite)
				self.Model.update({
					"firstname": invite.Firstname,
					"lastname": invite.Lastname,
					"senderName": invite.FromMember.fullname(),
					"senderMessage": invite.PersonalMessage,
					'form': form,
					'invite': invite
					})
				if invite.is_saved():
					self.Model.update({ "inviteKey": invite.key() })
				if invite.is_saved():
					self.Model.update({"messagePreview": invite.getMessage()})
					self.TemplateBase = os.path.dirname(__file__)
					self.render('views/membership-inviteNew-preview.html')
				else:
					self.TemplateBase = os.path.dirname(__file__)
					self.render('views/membership-inviteNew.html')
			else: self.error(404)

	def post(self, key):
		onRequest(self)
		if self.CurrentMember:
			if key: invite = Invite.get(key)
			else: invite = Invite(FromMember = self.CurrentMember)
			if invite:
				if self.request.get("doDiscard"):
					invite.Status = "discarded"
					invite.put()
					self.redirect('/Invites')
					return
				if self.request.get("doDelete"):
					invite.delete()
					self.redirect('/Invites')
					return
				form = InviteForm(data=self.request.POST, instance=invite)
				if form.is_valid() and self.request.get("doSend"):
					# Save the form, and redirect to the view page
					invite = form.save(commit=False)
					invite.put() #The invite must be persisted before the invite key is available to send
					invite.send()
					self.redirect('/Invites')
					return
				else:
					self.Model.update({
						"invite": invite,
						'form': form
						})
					if form.is_valid() and self.request.get("doPreview"):
						invite = form.save(commit=False)
						self.Model.update({"messagePreview": invite.getMessage()})
						self.TemplateBase = os.path.dirname(__file__)
						self.render('views/membership-inviteNew-preview.html')
					else:
						self.TemplateBase = os.path.dirname(__file__)
						self.render('views/membership-inviteNew.html')
			else: self.error(404)


class ProfilePhotoImage(webapp.RequestHandler):
	def get(self, key):
		onRequest(self)
		member = Member.get(key)
		if member:
			if member.ProfilePhoto:
				paramWidth = self.request.get("width")
				if paramWidth == "30":
					width = 30
					height = 30
				elif paramWidth == "80":
					width = 80
					height = 80
				elif paramWidth == "100":
					width = 100
					height = 100
				elif paramWidth == "120":
					width = 120
					height = 120
				elif paramWidth == "original":
					width = None
					height = None
				else:
					width = 50
					height = 50
				imageKey = "profilePhotoThumb" + str(width) + "-%s" % member.key()
				if width: thumbnailData = memcache.get(imageKey)
				if thumbnailData is None:
					image = images.Image(member.ProfilePhoto)
					if width: image.resize(width, height)
					image.rotate(0) # Because there needs to be at least one transformation to output as a JPEG
					thumbnailData = image.execute_transforms(output_encoding=images.JPEG)
					if width: memcache.add(imageKey, thumbnailData)

				self.response.headers['content-type'] = "image/png"
				self.response.headers['cache-control'] = "public, max-age=1814400" # 21 day cache
				self.response.headers["Expires"] = "Thu, 01 Dec 2014 16"
				self.response.out.write(thumbnailData)
			else:
				self.error(404)
		else:
			self.error(404)
