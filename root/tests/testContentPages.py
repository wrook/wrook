"""
Test suite for Wrook's content pages.

The tests cover the following content pages:
- Who is behind wrook
- Wrook is Open Source
- Half Baked Edition
- Attribution to Wrook
- CPAL 1.0 License

Those tests check is the page exists and if some key text fragments are there.
"""

from selenium import selenium
import unittest
import sys, time

class TestContent(unittest.TestCase):
	
	seleniumHost = 'localhost'
	seleniumPort = str(4444)
	browserStartCommand = "*firefox"
	#browserStartCommand = "c:\\program files\\internet explorer\\iexplore.exe"
	browserURL = "http://localhost:8080"

	def setUp(self):
		#print "Using selenium server at " + self.seleniumHost + ":" + self.seleniumPort
		self.selenium = selenium(self.seleniumHost, self.seleniumPort, self.browserStartCommand, self.browserURL)
		self.selenium.start()

	def testWhoIsBehindWrook(self):
		'''
		Tests the "Who is behind Wrook" content page.
		Test includes acces via the main navigation path from the home page.
		'''
		selenium = self.selenium
		selenium.open("/")
		selenium.wait_for_page_to_load("30000")
		selenium.click("menuWho")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-about-who", selenium.get_attribute("//body@id"))


	def testHalfBakedEdition(self):
		'''
		Tests the "Half Baked Edition" content page.
		Test includes acces via the main navigation path from the home page.
		'''
		selenium = self.selenium
		selenium.open("/")
		selenium.wait_for_page_to_load("30000")
		selenium.click("link-halfBaked")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-about-HalfBakedEdition", selenium.get_attribute("//body@id"))


	def testWrookIsOpenSource(self):
		'''
		Tests the "Wrook is Open Source" content page.
		Test includes acces via the main navigation path from the home page.
		'''
		selenium = self.selenium
		selenium.open("/")
		selenium.wait_for_page_to_load("30000")
		selenium.click("menu-openSourceLicense")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-about-OpenSourceLicense", selenium.get_attribute("//body@id"))
		selenium.click("menu-openSourceAttribution")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-about-openSourceAttribution", selenium.get_attribute("//body@id"))
		selenium.click("menu-CPAL10License")
		selenium.wait_for_page_to_load("30000")
		self.assertEqual("page-about-CPAL", selenium.get_attribute("//body@id"))


	def tearDown(self):
		self.selenium.stop()


if __name__ == "__main__":
    unittest.main()
