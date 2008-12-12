"""
cachetree module from the feathers toolkit
cachetree is a caching utility which provide basic cache invalidation through the use of composite keys.
"""

import datetime
import logging
from google.appengine.ext import db
from google.appengine.api import memcache

class Cachable(db.Model):
	Timestamp =  db.DateTimeProperty(auto_now_add=True)
		
	def touch(self):
		logging.info("in: touch(%s)" % self.key())
		self.Timestamp = datetime.datetime.now()
		self.update_cache()
		self.touch_up(self)

	def clear_cache(self):
		logging.info("in: clear_cache(%s)" % self.key())
		key = self.get_cache_key()
		memcache.delete(key)
		memcache.delete("%s-meta" % key)
		self.touch_up(self)
		logging.info("out: clear_cache(%s)" % self.key())
		return True

	def touch_up(self, childItem):
		'''
		Bubble up the touch event without systematically touching
		each parents in the process. By default, this process goes up
		the hierarchy of the entity group.
		
		Classes inheriting from Cachable should simply call the super class
		to let the bubbling chain continue its course.
		'''
		logging.info("in: touch_up(%s, %s)" % (self.key(), childItem.key()))
		if self.parent():
			if self.parent().touch_up:
				self.parent().touch_up(childItem)

	def update_cache(self):
		logging.info("update_cache(%s)" % self.get_cache_key())
		memcache.set(self.get_cache_key(), self)
		self.update_cache_meta()

	def update_cache_meta(self):
		#Refreshes the reference cache metadata
		meta = {"Timestamp": self.Timestamp}
		memcache.set("%s-meta" % self.get_cache_key(), meta)
	
	def get_cache_key(self):
		# Returns the simplest possible cache key for this asset
		# Should be overwritten if something more specific is needed
		return "%s" % self.key()
	

def get_fresh_cache(key, dependencyKeys):
	isFresh = True
	itemMeta = memcache.get("%s-meta" % key)
	timestamp = None
	if itemMeta:
		for depKey in dependencyKeys:
			logging.info("fetching meta: %s-meta " % depKey)
			meta = memcache.get("%s-meta" % depKey)
			if not meta: continue
			if not meta.get("Timestamp"): continue
			logging.info("comparing dep:%s > itm:%s " % (meta.get("Timestamp"), itemMeta.get("Timestamp")))
			if (meta.get("Timestamp") > itemMeta.get("Timestamp")):
				isFresh = False
				break
		if isFresh:
			logging.info("found: get_fresh_cache(%s, %s)" % (key, dependencyKeys))
			return memcache.get(key)
		logging.info("no meta (get_fresh_cache)")
	logging.info("not found: get_fresh_cache(%s, %s)" % (key, dependencyKeys))
	return None

def old_get(key):
	logging.info("cachetree.get(%s)" % key)
	#get timestamp from cache metadata
	if key:
		parentKey = key.split("::",1)[0]
		meta = memcache.get(key)
		if meta:
			parentMeta = memcache.get(parentKey)
			if not parentMeta:
				logging.info("Fresh cached data found: %s", key)
				return meta.get("data")
			logging.info("Comparing timestamps: %s > %s" %
				(meta.get("timestamp"), parentMeta.get("timestamp")))
			if meta.get("timestamp") > parentMeta.get("timestamp"):
				#if still valid get data from cache
				logging.info("Fresh cached data found: %s", key)
				return meta.get("data")
			else:
				logging.info("Cached data was stale: %s", key)
				return None
		else:
			logging.info("No cache found: %s", key)
			return None
	else:
		logging.info("No keys provided")
		return None


def touch(key):
	timestamp = datetime.datetime.now()
	meta = {"Timestamp": timestamp}
	memcache.set("%s-meta" % key, meta)

def get(key):
	logging.info("Getting cache data for : %s" % key )
	return memcache.get(key)

def add(key, data):
	logging.info("Caching data to : %s" % key )
	memcache.add(key, data)
	memcache.add("%s-meta" % key, {"Timestamp":datetime.datetime.now()})
	logging.info("Done caching to : %s" % key )

def set(key, data):
	logging.info("Caching data to : %s" % key )
	memcache.set(key, data)
	memcache.set("%s-meta" % key, {"Timestamp":datetime.datetime.now()})
	logging.info("Done caching to : %s" % key )


