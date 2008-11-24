"""
Storyline for the Membership module of Feathers.
"""

import sys

sys.path = sys.path + [
	'/Python25/Lib/site-packages',
	'/Python25/Lib/site-packages/epydoc',
	'/Program Files/Google/google_appengine',
	'/Program Files/Google/google_appengine/lib/django',
	'/Program Files/Google/google_appengine/lib/webob',
	'/Program Files/Google/google_appengine/lib/yaml/lib',
	'/Program Files/Google/google_appengine/google/appengine',
	'/wrook/root/latest/',
	'/wrook/root/latest/root',
	'/wrook/root/latest/root/feathers']

import storyline
import membership # Membership module
import testMembership # Membership tests


class MembershipStoryBook(storyline.Book):
	"""
	Main book for the Membership module.
	"""
	
	VisitorLoginWithEmail = storyline.Story()
	"""Visitor logs in using his email address."""
	
	VisitorLoginWithUsername = storyline.Story()
	"""Visitor logs in using his username."""
	
	MemberViewPublicProfile = storyline.Story()
	"""Member views his public profile"""

	MemberLogout = storyline.Story()
	"""Member logs out."""

	MemberViewHisAccountSettings = storyline.Story()
	"""Member views his account settings."""

	MemberEditAccountSettings = storyline.Story()
	"""Member edits his account settings."""

	MemberChangeProfilePhoto = storyline.Story()
	"""Member changes his profile photo."""

	MemberChangePassword = storyline.Story()
	"""Member changes his password."""

	VisitorJoinWrook = storyline.Story()
	"""Visitor joins Wrook."""

	MemberResetsHisPassword = storyline.Story()
	"""Member resets his password."""

	def __init__(self):
		self.add([membership])

		VisitorLoginWithEmail.add([
			self.Test(testMembership.TestMembership.testMemberLogsInWithEmailAddress),
			self.Interface(membership.memberLogin),
			membership.Member.login,
			membership.getMemberFromCredentials
			])

		VisitorLoginWithUsername.add([
			self.Test(testMembership.TestMembership.testMemberLogsInWithUsername),
			self.Interface(membership.memberLogin),
			membership.Member.login,
			membership.getMemberFromCredentials
			])

		MemberViewPublicProfile.add([
			self.Test(testMembership.TestMembership.testMemberVisitHisPublicProfile)
			])

		MemberLogout.add([
			self.Test(testMembership.TestMembership.testMemberLogout)
			])

		MemberViewHisAccountSettings.add([
			self.Test(testMembership.TestMembership.testMemberViewsAndEditsHisAccountSettings)
			])

		MemberEditAccountSettings.add([
			self.Test(testMembership.TestMembership.testMemberViewsAndEditsHisAccountSettings)
			])

		MemberChangePassword.add([
			self.Test(testMembership.TestMembership.testMemberChangePassword)
			])