#============================================================================
# STORIES


class StoryMemberStartReadingBook(stories.Story):
	ID = "MemberStartReadingBook"
	TitleTemplate = _('<a href="/Members/$MemberKey">$MemberFullname</a> started reading <a href="/Books/$BookKey">$BookTitle</a>')
	BodyTemplate = ""
	Icon = "book-open.png"
	
	def getTitle(self, params):
		member = params["member"]
		book = params["book"]
		data = {
			"MemberFullname": member.fullname(),
			"MemberKey": member.key(),
			"BookTitle": book.Title,
			"BookKey": book.key()
			}
		template = Template(self.TitleTemplate)
		return template.safe_substitute(data)
	
	def getTargets(self, params): #Get the list of member who will receive the story posts
		targets = []
		targets.append(params["book"].Author)
		targets.append(params["member"])
		return targets

class StorySiteCacheIsFlushed(stories.Story):
	"""This story warns all admins that the site cache has been flushed"""
	ID = "SiteCacheIsFlushed"
	TitleTemplate = _('<a href="/Members/$MemberKey">$MemberFullname</a> has flushed the site cache')
	BodyTemplate = ""
	Icon = "flush.png"
	
	def getTitle(self, params):
		member = params["member"]
		data = {
			"MemberFullname": member.fullname(),
			"MemberKey": member.key()
			}
		template = Template(self.TitleTemplate)
		return template.safe_substitute(data)
	
	def getTargets(self, params): #Get the list of member who will receive the story posts
		return membership.Member.all().filter("isAdmin =", True).fetch(limit=999)

