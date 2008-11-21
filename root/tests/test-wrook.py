"""
Test suite for Wrook.

Note: Tests are built as user stories. Many of those user stories will have
equivalent user stories in the specifications.
"""
from selenium import selenium
import unittest
import sys, time

class TestMembership(unittest.TestCase):

	seleniumHost = 'localhost'
	seleniumPort = str(4444)
	browserStartCommand = "*firefox"
	#browserStartCommand = "c:\\program files\\internet explorer\\iexplore.exe"
	browserURL = "http://localhost:8080"
	
	def setUp(self):
		print "Using selenium server at " + self.seleniumHost + ":" + self.seleniumPort
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
		selenium.open("/")
		selenium.wait_for_page_to_load("30000")
		selenium.click("menu-login")
		selenium.wait_for_page_to_load("30000")
		selenium.type("username", "mathieu@mathieu-sylvain.net")
		selenium.type("password", "zaq:l,kk")
		selenium.click("login")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-home-member", selenium.get_attribute("//body@id"))
	
	def testMemberLogsInWithUsername(self):
		'''Member logs in the system by using his username and password.'''
		selenium = self.selenium
		self.preconditionLoggedOut()
		selenium.click("menu-login")
		selenium.wait_for_page_to_load("30000")
		selenium.type("username", "MathieuSylvain")
		selenium.type("password", "zaq:l,kk")
		selenium.click("login")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-home-member", selenium.get_attribute("//body@id"))
	
	def testMemberVisitHisPublicProfile(self):
		'''Member visits his public profile. (Via URL)'''
		selenium = self.selenium
		self.preconditionLoggedIn()
		selenium.open("/")
		selenium.wait_for_page_to_load("30000")
		selenium.click("//a[@id='sidebarMenu-publicProfile']")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-members-stories", selenium.get_attribute("//body@id"))

	def tearDown(self):
		self.selenium.stop()


if __name__ == "__main__":
    unittest.main()
