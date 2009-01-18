#!python
# coding=UTF-8

from feathers import stories
from string import Template
import logging

class BookStoryOccurence(stories.StoryOccurence):
	from google.appengine.ext import db
	import books
	Book = db.ReferenceProperty(books.Book, collection_name="StoryOccurences")
	Chapter = db.ReferenceProperty(books.Chapter, collection_name="StoryOccurences")
	Revision = db.ReferenceProperty(books.Revision, collection_name="StoryOccurences")
	

class story_chapter_added(stories.Story):
	ID = "MemberAddsChapter"
	TitleTemplate = _('<a href="/Members/$MemberKey">$MemberFullname</a> created a new chapter called $ChapterTitle in  <a href="/Books/$BookKey/Contents#$ChapterKey">$BookTitle</a>')
	BodyTemplate = ""
	Icon = "book-open.png"
	StoryOccurenceClass = BookStoryOccurence

	def getTitle(self, params):
		member = params["member"]
		book = params["book"]
		chapter = params["chapter"]
		data = {
			"MemberFullname": unicode(member.fullname()),
			"MemberKey": member.key(),
			"BookTitle": unicode(book.Title),
			"BookKey": book.key(),
			"ChapterTitle": unicode(chapter.Title),
			"ChapterKey": chapter.key()
			}
		template = Template(unicode(self.TitleTemplate))
		return template.safe_substitute(data)
	
	def getTargets(self, params): #Get the list of member who will receive the story posts
		targets = []
		targets.append(params["book"].Author)
		return targets

	def on_create_occurence(self, occurence, params):
		occurence.Book = params["book"].key()
		occurence.Chapter = params["chapter"].key()
		return occurence


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
