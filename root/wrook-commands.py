
def remove_labs():
	"""
	Remove all entities related to the old "Labs" module which has been removed from the project.
	"""
	from google.appengine.ext import db
	class Release(db.Model):
		pass
	class Feature(db.Model):
		pass
	class Vote(db.Model):
		pass
	db.delete(Release.all())
	db.delete(Feature.all())
	db.delete(Vote.all())


def reset_member_for_searchable_model():
	"""
	Resaves member entities for them to support the features of the searchable model.
	"""
	from feathers import membership
	members = membership.Member.all().fetch(limit=1000)
	for member in members:
		member.Firstname = member.Firstname
		member.Lastname = member.Lastname
		member.save()
	print "Success: All members have been updated!"

def reset_member_hasProfilePhoto():
	"""
	Sets the correct value on the hasProfilePhoto property for all members.
	"""
	from feathers import membership
	members = membership.Member.all().fetch(limit=1000)
	for member in members:
		if member.ProfilePhoto:
			member.hasProfilePhoto = True
		else:
			member.hasProfilePhoto = False
		member.put()
	print "Success: All hasProfilePhoto properties have been set!"