"""
WROOK LICENSING MODULE
 
This module controls the licensing aspects of books. It offers the necessary
models, methods and license data needed to offer licensing options for books.

Covered user stories:
	- The user selects the type of license for this books
	- The user specify that the book is from another author
	- When reading a book, the user views the licensing information
	- When reading a book, the user follow's a link to find more information about the license

"""
from google.appengine.ext import db

class LicenseType(db.Model):
	Id = db.StringProperty()
	Title = db.StringProperty()
	ShortDescription =  db.TextProperty()
	URL = db.StringProperty()

	def __unicode__(self):
		return self.Title

def LoadLicenseTypes():
	db.delete(LicenseType.all())
	for licenseID in LicenseTypes:
		LicenseTypes.get(licenseID).put()


LicenseTypes = {}
LicenseTypes.update({"deriv-fair-use": LicenseType(
	Id="deriv-fair-use",
	Title="Derivative Work Under Fair Use",
	URL="",
	ShortDescription="")})
LicenseTypes.update({"copyright": LicenseType(
	Id="copyright",
	Title="Copyright All rights reserved",
	URL="",
	ShortDescription="")})
LicenseTypes.update({"public-domain": LicenseType(
	Id="public-domain",
	Title="Public Domain Dedication",
	URL="http://creativecommons.org/licenses/publicdomain/",
	ShortDescription="")})
LicenseTypes.update({"cc-by": LicenseType(
	Id="cc-by",
	Title="CC Attribution Alone (by)",
	URL="http://creativecommons.org/licenses/by/3.0/",
	ShortDescription="")})
LicenseTypes.update({"cc-by-nc": LicenseType(
	Id="cc-by-nc",
	Title="CC Attribution, Noncommercial (by-nc)",
	URL="http://creativecommons.org/licenses/by-nc/3.0/",
	ShortDescription="")})
LicenseTypes.update({"cc-by-nd": LicenseType(
	Id="cc-by-nd",
	Title="CC Attribution, No Derivatives (by-nd)",
	URL="http://creativecommons.org/licenses/by-nd/3.0/",
	ShortDescription="")})
LicenseTypes.update({"cc-by-sa": LicenseType(
	Id="cc-by-sa",
	Title="CC Attribution-Share Alike (by-sa)",
	URL="http://creativecommons.org/licenses/by-sa/3.0/",
	ShortDescription="")})
LicenseTypes.update({"cc-by-nc-nd": LicenseType(
	Id="cc-by-nc-nd",
	Title="CC Attribution-Noncommercial-No Derivatives (by-nc-nd)",
	URL="http://creativecommons.org/licenses/by-nc-nd/3.0/",
	ShortDescription="")})
LicenseTypes.update({"cc-by-nc-sa": LicenseType(
	Id="cc-by-nc-sa",
	Title="CC Attribution-Noncommercial-Share Alike (by-nc-sa)",
	URL="http://creativecommons.org/licenses/by-nc-sa/3.0/",
	ShortDescription="")})
LicenseTypes.update({"free-art-license": LicenseType(
	Id="free-art-license",
	Title="Free Art License 1.3",
	URL="http://artlibre.org/licence/lal/en/",
	ShortDescription="")})

LicenseTypes.update({"other": LicenseType(
	Id="other",
	Title="Other...",
	URL="",
	ShortDescription="")})
