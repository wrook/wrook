#!python
# coding=UTF-8

from feathers import stories
from string import Template
import logging

class StoryMemberStartReadingBook(stories.Story):
	ID = "MemberStartReadingBook"
	TitleTemplate = _('<a href="/Members/$MemberKey">$MemberFullname</a> started reading <a href="/Books/$BookKey">$BookTitle</a>')
	BodyTemplate = ""
	Icon = "book-open.png"
	
	def getTitle(self, params):
		member = params["member"]
		book = params["book"]
		data = {
			"MemberFullname": unicode(member.fullname()),
			"MemberKey": member.key(),
			"BookTitle": unicode(book.Title),
			"BookKey": book.key()
			}
		template = Template(unicode(self.TitleTemplate))
		return template.safe_substitute(data)
	
	def getTargets(self, params): #Get the list of member who will receive the story posts
		targets = []
		targets.append(params["book"].Author)
		targets.append(params["member"])
		return targets
