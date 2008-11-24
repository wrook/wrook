"""
The storyline module.

The storyline is a lightweight module lets you define your user stories as a
mixture of executable code and declarative data. Those stories can then be
acted upon to provide reporting, coverage analysis, documentation generation
and other artsy fartsy mumbo jumbo.

Storylines integrates with existing Docstrings and PyUnit standard modules
to create rich and verifiable fucntionnal specifications which complement
existing Code/API documentations and unit testing.

One basic thing you can do is attach specific test cases to your stories and
books to later report on the "functionnal" coverage your tests are offering.

Also, a similar thing can be done by attaching multiple modules and methods to
each user stories. This way, any code that would be removed during maintenance
would have verifiable repercution on your executable documentation at runtime.

In addition, a well annotated storyline will enable you to publish
automatically your user stories by using documentation generation tools
such as Epydoc.

In other words, the basic concept is to build documentation which is healthy
when the code is ealthy and sick when the code is sick. Thus forcing
developpers to keep both alive and well.

"""
class Book:
	"""
	Books are the functionnal equivalent of a software module.
	
	Books are a container for Stories. Books can be instanciated for them to
	be acted upon and manipulated.
	"""

	Reference = []

	def add(self, items):
		"""Add a code reference which is associated to that book."""
		for item in items:
			self.Reference.append(item)
		return self

	def Test(reference):
		return reference;

	def Interface(reference):
		return reference;

class Story:
	"""Stories correspond to "User Stories" as defined by agile methodologies."""

	Reference = []

	def add(self, items):
		"""Add a code reference which is associated to that story."""
		for item in items:
			self.Reference.append(item)
		return self

