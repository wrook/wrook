from string import Template
import stories

class aa():
	
	class StoryMemberPostsTopicOnBook(stories.Story):
		ID = "MemberPostsTopicOnBook"
		TitleTemplate = _('<a href="/Members/$MemberKey">$MemberFullname</a> has posted a new topic under <a href="ParentURL">$ParentTitle</a>')
		BodyTemplate = _('''
	<strong>The message said: $TopicTitle </strong>
	<br />"&#160;$TopicBody&#160;"
	''')
		Icon = "comment.png"
	
		#The way by which the data "property bag" is handled is needlessly
		#Cumbersome... this should be simplified
		def getTitle(self, params):
			member = params["member"]
			parentURL = params["parentURL"]
			parentTitle = params["parentTitle"]
			data = {
				"MemberFullname": member.fullname(),
				"MemberKey": member.key(),
				"ParentTitle": parentTitle,
				"ParentURL": parentURL
				}
			template = Template(self.TitleTemplate)
			return template.safe_substitute(data)
	
		def getBody(self, params):
			member = params["member"]
			topic = params["topic"]
			parentURL = params["parentURL"]
			parentTitle = params["parentTitle"]
			data = {
				"MemberFullname": member.fullname(),
				"MemberAvatar": member.gravatar30(),
				"MemberKey": member.key(),
				"ParentTitle": parentTitle,
				"ParentURL": parentURL,
				"TopicTitle": topic.Title,
				"TopicBody": topic.Body
				}
			template = Template(self.BodyTemplate)
			return template.safe_substitute(data)
	
		def getTargets(self, params): #Get the list of member who will receive the story posts
			targets = []
			if params["recipient"]:
				targets.append(membership.Member.get(params["recipient"]))
			targets.append(params["member"])
			return targets
	
