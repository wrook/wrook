"""
Test suite for Wrook's membership module.
"""

from selenium import selenium
import unittest
import sys, time

class TestMembership(unittest.TestCase):
	
	testMemberUsername = "MathieuSylvain"
	testMemberEmail = "mathieu@mathieu-sylvain.net"
	testMemberPassword = "zaq:l,kk"
	testMemberAlternatePassword = "yabadabadou"

	seleniumHost = 'localhost'
	seleniumPort = str(4444)
	browserStartCommand = "*firefox"
	#browserStartCommand = "c:\\program files\\internet explorer\\iexplore.exe"
	browserURL = "http://localhost:8080"
	
	def setUp(self):
		#print "Using selenium server at " + self.seleniumHost + ":" + self.seleniumPort
		self.selenium = selenium(self.seleniumHost, self.seleniumPort, self.browserStartCommand, self.browserURL)
		self.selenium.start()

	def testMemberLogout(self):
		'''Logged in member logs out (via URL)'''
		self.doMemberLogout()

	def doMemberLogout(self):
		selenium = self.selenium
		selenium.open("/Logout")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-home-visitor", selenium.get_attribute("//body@id"))
	
	def preconditionLoggedOut(self):
		'''Logs out the member if he is logged in, otherwise do nothing.'''
		selenium = self.selenium
		selenium.open("/")
		selenium.wait_for_page_to_load("30000")
		hasUsername = selenium.is_element_present("//meta[@name='wrook.username']")
		if hasUsername: self.doMemberLogout()
	
	def preconditionLoggedIn(self):
		'''Logs in member if he is logged out, otherwise do nothing.'''
		selenium = self.selenium
		selenium.open("/")
		selenium.wait_for_page_to_load("30000")
		hasUsername = selenium.is_element_present("//meta[@name='wrook.username']")
		if not hasUsername: self.doMemberLogsInWithEmailAddress()
			
	
	def testMemberLogsInWithEmailAddress(self):
		'''Member logs in the system by using his email address and password.'''
		self.preconditionLoggedOut()
		self.doMemberLogsInWithEmailAddress()

	def doMemberLogsInWithEmailAddress(self):
		selenium = self.selenium
		self.preconditionLoggedOut()
		self.doMemberLogin(self.testMemberEmail, self.testMemberPassword)

	def testMemberLogsInWithUsername(self):
		'''Member logs in the system by using his username and password.'''
		selenium = self.selenium
		self.preconditionLoggedOut()
		self.doMemberLogin(self.testMemberUsername, self.testMemberPassword)

	def doMemberLogin(self, usernameOrEmail, password):
		selenium = self.selenium
		selenium.click("menu-login")
		selenium.wait_for_page_to_load("30000")
		selenium.type("username", usernameOrEmail)
		selenium.type("password", password)
		selenium.click("login")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-home-member", selenium.get_attribute("//body@id"))
	
	def testMemberVisitHisPublicProfile(self):
		'''Member visits his public profile. (Via URL)'''
		selenium = self.selenium
		self.preconditionLoggedIn()
		selenium.open("/")
		selenium.wait_for_page_to_load("30000")
		selenium.click("sidebarMenu-publicProfile")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-members-stories", selenium.get_attribute("//body@id"))

	def testMemberViewsAndEditsHisAccountSettings(self):
		'''
		Member views and edits his account settings.
		Persistance is tested by changing the about field twice
		and verifying the saved input
		'''
		selenium = self.selenium
		self.preconditionLoggedIn()
		selenium.open("/")
		selenium.wait_for_page_to_load("30000")
		selenium.click("sidebarMenu-accountSettings")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-account-view", selenium.get_attribute("//body@id"))
		selenium.click("btnEditAccount")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-account-edit", selenium.get_attribute("//body@id"))
		selenium.type("About", "Bonjour!")
		selenium.click("btnSave")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-account-view", selenium.get_attribute("//body@id"))
		self.assertEqual("Bonjour!", selenium.get_text("valAbout"))
		selenium.click("btnEditAccount")
		selenium.wait_for_page_to_load("30000")

	def testMemberChangePassword(self):
		'''
		Member logs in with the default password, changes his password, then
		logs out and logs back in with the new password.
		Afterward, the member changes back the password to the default.
		'''
		def browseToChangePasswordFromHome():
			selenium.click("sidebarMenu-accountSettings")
			selenium.wait_for_page_to_load("30000")
			self.assertEqual("page-account-view", selenium.get_attribute("//body@id"))
			selenium.click("sidebarMenu-changePassword")
			selenium.wait_for_page_to_load("30000")
			self.assertEqual("page-account-changePassword", selenium.get_attribute("//body@id"))

		selenium = self.selenium
		self.preconditionLoggedIn()
		browseToChangePasswordFromHome()
		selenium.type("oldPassword", self.testMemberPassword)
		selenium.type("newPassword", self.testMemberAlternatePassword)
		selenium.click("save")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-account-view", selenium.get_attribute("//body@id"))
		self.doMemberLogout()
		self.doMemberLogin(self.testMemberUsername, self.testMemberAlternatePassword)
		browseToChangePasswordFromHome()
		selenium.type("oldPassword", self.testMemberAlternatePassword)
		selenium.type("newPassword", self.testMemberPassword)
		selenium.click("save")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-account-view", selenium.get_attribute("//body@id"))
		self.doMemberLogout()
		self.doMemberLogin(self.testMemberUsername, self.testMemberPassword)

		def browseToChangePasswordFromHome():
			selenium.click("sidebarMenu-accountSettings")
			selenium.wait_for_page_to_load("30000")
			self.assertEqual("page-account-view", selenium.get_attribute("//body@id"))
			selenium.click("sidebarMenu-changePassword")
			selenium.wait_for_page_to_load("30000")
			self.assertEqual("page-account-changePassword", selenium.get_attribute("//body@id"))



	def tearDown(self):
		self.selenium.stop()


if __name__ == "__main__":
    unittest.main()
